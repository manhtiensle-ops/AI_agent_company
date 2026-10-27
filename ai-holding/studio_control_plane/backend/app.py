import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared_core.agent_provisioner import unlink_and_clone, spawn_subordinate
from shared_core.config import (
    AI_HOLDING_ROOT,
    B2B_CONTRACTS_PATH,
    COMPANIES_DIR,
    DEVOPS_DIR,
    GLOBAL_LIMITS_PATH,
    RESOURCES_DB_PATH,
    MESSAGES_DB_PATH,
)
from shared_core.db_manager import (
    get_db_connection,
    post_message,
    rollback_execution_steps,
    update_agent_runtime_state,
)

app = FastAPI(title="AI Holding Studio Control Plane", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_websockets: List[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)


async def broadcast_ws(event: str, data: Any):
    payload = json.dumps({"event": event, "data": data}, ensure_ascii=False)
    for ws in list(connected_websockets):
        try:
            await ws.send_text(payload)
        except Exception:
            pass


# --- 1. TOPOLOGY CANVAS API (React Flow Graph) ---

@app.get("/api/topology")
def get_topology() -> Dict[str, Any]:
    nodes = []
    edges = []

    # 1. DevOps Cluster Node
    devops_master = DEVOPS_DIR / "My_credential_devops_hermes"
    if devops_master.exists():
        is_shared = devops_master.is_symlink()
        nodes.append({
            "id": "devops_master",
            "type": "agentNode",
            "data": {
                "label": "My_credential_devops_hermes",
                "role": "Master Infrastructure Router",
                "path": "shared_core/devops_ministry/My_credential_devops_hermes",
                "cluster": "devops",
                "mode": "SHARED" if is_shared else "CLONED"
            },
            "position": {"x": 400, "y": 50}
        })

    # DevOps Specialists
    specs_dir = DEVOPS_DIR / "specialists"
    if specs_dir.exists():
        idx = 0
        for s in sorted(specs_dir.iterdir()):
            if s.is_dir() or s.is_symlink():
                s_id = f"spec_{s.name}"
                nodes.append({
                    "id": s_id,
                    "type": "specialistNode",
                    "data": {
                        "label": s.name,
                        "role": "DevOps Specialist",
                        "path": f"shared_core/devops_ministry/specialists/{s.name}",
                        "cluster": "devops",
                        "mode": "SHARED" if s.is_symlink() else "CLONED"
                    },
                    "position": {"x": 100 + idx * 160, "y": 180}
                })
                edges.append({
                    "id": f"edge_devops_{s_id}",
                    "source": "devops_master",
                    "target": s_id,
                    "animated": True,
                    "style": {"stroke": "#06b6d4"}
                })
                idx += 1

    # 2. Companies Cluster
    comp_x = 100
    if COMPANIES_DIR.exists():
        for comp in sorted(COMPANIES_DIR.iterdir()):
            if not comp.is_dir():
                continue
            comp_id = f"comp_{comp.name}"
            nodes.append({
                "id": comp_id,
                "type": "companyNode",
                "data": {
                    "label": comp.name,
                    "path": f"companies/{comp.name}",
                    "cluster": "company"
                },
                "position": {"x": comp_x, "y": 320}
            })

            # Check for CEO
            ceo_candidates = [d for d in comp.iterdir() if d.is_dir() and "CEO" in d.name]
            ceo_id = None
            if ceo_candidates:
                ceo = ceo_candidates[0]
                ceo_id = f"ceo_{comp.name}_{ceo.name}"
                nodes.append({
                    "id": ceo_id,
                    "type": "ceoNode",
                    "data": {
                        "label": ceo.name,
                        "company": comp.name,
                        "path": f"companies/{comp.name}/{ceo.name}",
                        "mode": "SHARED" if ceo.is_symlink() else "CLONED"
                    },
                    "position": {"x": comp_x + 50, "y": 420}
                })
                edges.append({
                    "id": f"edge_{comp_id}_{ceo_id}",
                    "source": comp_id,
                    "target": ceo_id,
                    "style": {"stroke": "#10b981"}
                })

            # Departments
            depts_dir = comp / "departments"
            dept_y = 540
            if depts_dir.exists():
                for dept in sorted(depts_dir.iterdir()):
                    if not dept.is_dir():
                        continue
                    dept_id = f"dept_{comp.name}_{dept.name}"
                    nodes.append({
                        "id": dept_id,
                        "type": "deptNode",
                        "data": {
                            "label": dept.name,
                            "path": f"companies/{comp.name}/departments/{dept.name}",
                            "company": comp.name
                        },
                        "position": {"x": comp_x, "y": dept_y}
                    })
                    if ceo_id:
                        edges.append({
                            "id": f"edge_{ceo_id}_{dept_id}",
                            "source": ceo_id,
                            "target": dept_id,
                            "style": {"stroke": "#6366f1"}
                        })

                    # Workers
                    workers_dir = dept / "workers"
                    if workers_dir.exists():
                        w_idx = 0
                        for w in sorted(workers_dir.iterdir()):
                            if w.is_dir() or w.is_symlink():
                                w_id = f"worker_{comp.name}_{dept.name}_{w.name}"
                                nodes.append({
                                    "id": w_id,
                                    "type": "workerNode",
                                    "data": {
                                        "label": w.name,
                                        "path": f"companies/{comp.name}/departments/{dept.name}/workers/{w.name}",
                                        "mode": "SHARED" if w.is_symlink() else "CLONED"
                                    },
                                    "position": {"x": comp_x - 50 + w_idx * 140, "y": dept_y + 110}
                                })
                                edges.append({
                                    "id": f"edge_{dept_id}_{w_id}",
                                    "source": dept_id,
                                    "target": w_id,
                                    "style": {"stroke": "#a855f7"}
                                })
                                w_idx += 1
                    dept_y += 200

            comp_x += 450

    # 3. B2B Golden Bridge Edges
    if B2B_CONTRACTS_PATH.exists():
        try:
            contracts = json.loads(B2B_CONTRACTS_PATH.read_text(encoding="utf-8")).get("contracts", [])
            for c in contracts:
                if c.get("status") == "ACTIVE":
                    comp1 = c.get("company_1")
                    comp2 = c.get("company_2")
                    # Connect the CEOs
                    c1_node = next((n["id"] for n in nodes if n["data"].get("company") == comp1 and "CEO" in n["data"].get("label", "")), None)
                    c2_node = next((n["id"] for n in nodes if n["data"].get("company") == comp2 and "CEO" in n["data"].get("label", "")), None)
                    if c1_node and c2_node:
                        edges.append({
                            "id": f"b2b_{c.get('contract_id')}",
                            "source": c1_node,
                            "target": c2_node,
                            "animated": True,
                            "label": f"🤝 B2B Bridge: {c.get('scope', '')}",
                            "style": {"stroke": "#f59e0b", "strokeWidth": 3}
                        })
        except Exception:
            pass

    return {"nodes": nodes, "edges": edges}


# --- 2. HOT-EDITOR API (Atomic Read/Write & Blast Radius) ---

class FileContentRequest(BaseModel):
    path: str
    content: str


@app.get("/api/agent/files")
def get_agent_files(agent_path: str) -> Dict[str, Any]:
    target = AI_HOLDING_ROOT / agent_path.strip("/")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Agent path not found: {agent_path}")

    is_shared = target.is_symlink()
    soul = ""
    for s_name in ["agent_soul.md", "SOUL.md"]:
        f = target / s_name
        if f.exists():
            soul = f.read_text(encoding="utf-8")
            break

    memory = ""
    for m_name in ["agent_memory.md", "MEMORY.md"]:
        f = target / m_name
        if f.exists():
            memory = f.read_text(encoding="utf-8")
            break

    # Blast radius detection
    blast_radius = []
    if is_shared:
        real_target = target.resolve()
        for root, dirs, _ in os.walk(AI_HOLDING_ROOT):
            for d in dirs:
                full_p = Path(root) / d
                if full_p.is_symlink():
                    try:
                        if full_p.resolve() == real_target:
                            blast_radius.append(str(full_p.relative_to(AI_HOLDING_ROOT)))
                    except Exception:
                        pass

    return {
        "agent_path": agent_path,
        "is_shared": is_shared,
        "blast_radius": blast_radius,
        "soul": soul,
        "memory": memory,
        "is_paused": (target / ".paused").exists()
    }


@app.post("/api/agent/save-file")
def save_agent_file(req: FileContentRequest) -> Dict[str, Any]:
    file_path = AI_HOLDING_ROOT / req.path.strip("/")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write via .tmp
    tmp_path = file_path.with_suffix(".tmp")
    tmp_path.write_text(req.content, encoding="utf-8")
    os.replace(tmp_path, file_path)

    return {"status": "SUCCESS", "path": req.path}


@app.post("/api/agent/unlink-and-clone")
def unlink_agent(payload: Dict[str, str]) -> Dict[str, Any]:
    agent_path = payload.get("agent_path", "")
    target = AI_HOLDING_ROOT / agent_path.strip("/")
    return unlink_and_clone(target)


# --- 3. PAUSE - RESUME - TIMELINE - ROLLBACK API ---

@app.post("/api/agent/pause")
def pause_agent(payload: Dict[str, str]) -> Dict[str, Any]:
    agent_path = payload.get("agent_path", "")
    target = AI_HOLDING_ROOT / agent_path.strip("/")
    flag = target / ".paused"
    flag.write_text("PAUSED_BY_CHAIRMAN", encoding="utf-8")
    update_agent_runtime_state(agent_path, "CLONED", "PAUSED", "Execution paused by Chairman")
    return {"status": "PAUSED", "agent_path": agent_path}


@app.post("/api/agent/resume")
def resume_agent(payload: Dict[str, str]) -> Dict[str, Any]:
    agent_path = payload.get("agent_path", "")
    target = AI_HOLDING_ROOT / agent_path.strip("/")
    flag = target / ".paused"
    if flag.exists():
        flag.unlink()
    update_agent_runtime_state(agent_path, "CLONED", "IDLE", "Resumed by Chairman")
    return {"status": "RESUMED", "agent_path": agent_path}


@app.get("/api/agent/timeline")
def get_timeline(agent_path: str) -> List[Dict[str, Any]]:
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, step_num, agent_path, thought, tool_call, tool_output, memory_snapshot, created_at
            FROM execution_steps
            WHERE agent_path = ?
            ORDER BY id ASC
        """, (agent_path,))
        return [dict(r) for r in cursor.fetchall()]


@app.post("/api/agent/rollback")
def rollback_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    agent_path = payload.get("agent_path", "")
    step_num = int(payload.get("step_num", 1))

    snapshot = rollback_execution_steps(agent_path, step_num)
    target = AI_HOLDING_ROOT / agent_path.strip("/")

    # Restore memory snapshot if available
    if snapshot:
        mem_file = target / "agent_memory.md"
        if not mem_file.exists() and (target / "MEMORY.md").exists():
            mem_file = target / "MEMORY.md"
        mem_file.write_text(snapshot, encoding="utf-8")

    # Remove pause flag so agent can replay
    flag = target / ".paused"
    if flag.exists():
        flag.unlink()

    update_agent_runtime_state(agent_path, "CLONED", "IDLE", f"Rolled back to step #{step_num}")
    return {"status": "ROLLED_BACK", "agent_path": agent_path, "target_step": step_num}


# --- 4. CHAIRMAN COMMAND & MEETING INTERCEPTOR ---

class ChairmanCommandRequest(BaseModel):
    command: str
    target_channel: Optional[str] = "DIRECT"
    receiver_path: Optional[str] = None


@app.post("/api/chairman/command")
def execute_chairman_command(req: ChairmanCommandRequest) -> Dict[str, Any]:
    cmd = req.command.strip()

    # B2B Approval Command: "Cho phép Company_A_Bakery và Company_B_Soda hợp tác..."
    if "hợp tác" in cmd.lower() or "liên doanh" in cmd.lower():
        parts = cmd.split()
        comp1 = next((p for p in parts if "Bakery" in p or "A" in p), "Company_A_Bakery")
        comp2 = next((p for p in parts if "Soda" in p or "B" in p), "Company_B_Soda")

        contracts_data = {"contracts": []}
        if B2B_CONTRACTS_PATH.exists():
            try:
                contracts_data = json.loads(B2B_CONTRACTS_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass

        new_contract = {
            "contract_id": f"B2B_{comp1.upper()}_{comp2.upper()}_01",
            "company_1": comp1,
            "company_2": comp2,
            "allowed_representatives": [f"{comp1}/CEO", f"{comp2}/CEO"],
            "scope": cmd,
            "status": "ACTIVE"
        }
        contracts_data["contracts"].append(new_contract)
        B2B_CONTRACTS_PATH.write_text(json.dumps(contracts_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "status": "B2B_CONTRACT_ACTIVATED",
            "contract": new_contract,
            "message": f"Chairman approved B2B collaboration between {comp1} and {comp2}."
        }

    # Spawn Company / Subordinate command:
    if "tạo công ty" in cmd.lower():
        words = cmd.split()
        comp_name = "Company_New"
        for w in words:
            if "company_" in w.lower():
                comp_name = w.strip("`'\",")

        res = spawn_subordinate(
            caller_path="Chairman/Root_Hermes",
            target_unit_type="company_ceo",
            new_agent_name="CEO",
            base_archetype="CEO_Archetype",
            company_name=comp_name,
            initial_task_message=cmd
        )
        return {"status": "COMPANY_CREATED", "company_name": comp_name, "ceo": res}

    # Direct message to an agent or room
    receiver = req.receiver_path or "shared_core/devops_ministry/My_credential_devops_hermes"
    msg_id = post_message(
        sender_path="Chairman/Root_Hermes",
        receiver_path=receiver,
        channel_type=req.target_channel or "DIRECT",
        payload={"instruction": cmd, "from": "Chairman"}
    )
    return {"status": "MESSAGE_POSTED", "message_id": msg_id, "receiver": receiver}


@app.get("/api/resources")
def get_resources() -> Dict[str, Any]:
    with get_db_connection(RESOURCES_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM service_accounts ORDER BY id ASC")
        accounts = [dict(r) for r in cursor.fetchall()]
        return {"service_accounts": accounts}


# --- 5. STATIC FILES (Frontend Build Integration) ---
dist_dir = AI_HOLDING_ROOT / "studio_control_plane" / "frontend" / "dist"
if dist_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
