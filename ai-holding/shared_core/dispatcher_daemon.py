import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from shared_core.config import (
    AI_HOLDING_ROOT,
    MESSAGES_DB_PATH,
    OMNIROUTE_API_KEY,
    OMNIROUTE_URL,
)
from shared_core.db_manager import (
    get_db_connection,
    get_pending_messages,
    post_message,
    record_execution_step,
    update_agent_runtime_state,
    update_message_status,
)
from shared_core.devops_ministry.router import DevOpsMinistryRouter
from shared_core.rbac_router import validate_communication_permission

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dispatcher")


def get_agent_directory(agent_path: str) -> Path:
    p = Path(agent_path)
    if p.is_absolute():
        return p
    return AI_HOLDING_ROOT / p


def load_agent_instructions(agent_dir: Path) -> Dict[str, str]:
    soul_content = ""
    for s_name in ["agent_soul.md", "SOUL.md"]:
        f = agent_dir / s_name
        if f.exists():
            soul_content = f.read_text(encoding="utf-8")
            break

    memory_content = ""
    for m_name in ["agent_memory.md", "MEMORY.md"]:
        f = agent_dir / m_name
        if f.exists():
            memory_content = f.read_text(encoding="utf-8")
            break

    return {"soul": soul_content, "memory": memory_content}


def save_agent_memory(agent_dir: Path, new_memory: str) -> None:
    target_file = agent_dir / "agent_memory.md"
    if not target_file.exists() and (agent_dir / "MEMORY.md").exists():
        target_file = agent_dir / "MEMORY.md"

    # Atomic write
    tmp_file = target_file.with_suffix(".tmp")
    tmp_file.write_text(new_memory, encoding="utf-8")
    os.replace(tmp_file, target_file)


def is_agent_paused(agent_dir: Path) -> bool:
    return (agent_dir / ".paused").exists()


async def call_omniroute_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "auto/best-coding"
) -> Dict[str, Any]:
    """Calls OmniRoute gateway (http://localhost:20128/v1) with resilient error handling."""
    url = f"{OMNIROUTE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "content": content,
            "tokens": usage.get("total_tokens", 0)
        }


class DispatcherDaemon:
    def __init__(self, check_interval: float = 0.5):
        self.check_interval = check_interval
        self.devops_router = DevOpsMinistryRouter()
        self.running = False

    async def process_single_message(self, msg: Dict[str, Any]) -> None:
        msg_id = msg["id"]
        sender = msg["sender_path"]
        receiver = msg["receiver_path"]
        channel = msg["channel_type"]
        payload = msg["payload"]

        receiver_dir = get_agent_directory(receiver)

        # 1. Check if receiver is paused
        if is_agent_paused(receiver_dir):
            logger.info(f"Agent '{receiver}' is paused by Chairman (.paused flag present). Skipping.")
            update_agent_runtime_state(receiver, "CLONED", "PAUSED", "Execution paused by Chairman")
            return

        # 2. Check RBAC Communication Permission
        allowed, reason = validate_communication_permission(sender, receiver, channel)
        if not allowed:
            logger.warning(f"RBAC Block: {reason}")
            update_message_status(msg_id, "FAILED")
            post_message(
                sender_path="system/rbac_firewall",
                receiver_path=sender,
                channel_type="DIRECT",
                payload={"error": "RBAC_PERMISSION_DENIED", "details": reason, "original_message_id": msg_id}
            )
            return

        # 3. Mark message PROCESSING and Agent THINKING
        update_message_status(msg_id, "PROCESSING")
        mode = "SHARED" if receiver_dir.is_symlink() else "CLONED"
        update_agent_runtime_state(receiver, mode, "THINKING", f"Processing {channel} message from {sender}")

        try:
            # Check special routing: DevOps Tickets
            if "devops_ministry" in receiver and channel == "DEVOPS_TICKET":
                logger.info(f"Handling DevOps Ticket for {sender}...")
                ticket_res = self.devops_router.handle_ticket(payload)
                # Respond back to requester
                post_message(
                    sender_path=receiver,
                    receiver_path=sender,
                    channel_type="DIRECT",
                    payload={"ticket_response": ticket_res}
                )
                record_execution_step(
                    step_num=1,
                    agent_path=receiver,
                    thought="Processed infrastructure service ticket via DevOps specialists",
                    tool_call="DevOpsMinistryRouter.handle_ticket",
                    tool_output=json.dumps(ticket_res, ensure_ascii=False),
                    memory_snapshot="DevOps directory verified"
                )
                update_message_status(msg_id, "DONE")
                update_agent_runtime_state(receiver, mode, "IDLE", "DevOps Ticket resolved", 0)
                return

            # Standard Agent Processing
            instructions = load_agent_instructions(receiver_dir)
            system_prompt = f"{instructions['soul']}\n\n## BỘ NHỚ HIỆN TẠI (MEMORY):\n{instructions['memory']}"
            user_prompt = f"Tin nhắn từ [{sender}] qua kênh [{channel}]:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"

            llm_result = await call_omniroute_llm(system_prompt, user_prompt)
            content = llm_result["content"]
            tokens = llm_result["tokens"]

            # Record Execution Step
            record_execution_step(
                step_num=1,
                agent_path=receiver,
                thought=f"Responded to {channel} message",
                tool_call=None,
                tool_output=content[:200],
                memory_snapshot=instructions["memory"][:200]
            )

            # Update memory if agent included memory update tag
            if "## UPDATE_MEMORY:" in content:
                parts = content.split("## UPDATE_MEMORY:")
                new_mem = parts[1].strip()
                save_agent_memory(receiver_dir, new_mem)

            # Process Autonomous Actions
            await self._process_agent_actions(receiver, receiver_dir, content)

            update_message_status(msg_id, "DONE")
            update_agent_runtime_state(receiver, mode, "IDLE", "Awaiting next task", tokens)
            logger.info(f"Message #{msg_id} to '{receiver}' successfully completed.")

        except Exception as e:
            logger.error(f"Error processing message #{msg_id} for '{receiver}': {e}", exc_info=True)
            update_message_status(msg_id, "FAILED")
            update_agent_runtime_state(receiver, mode, "ERROR", f"Failed: {str(e)}")

    async def _process_agent_actions(self, agent_path: str, agent_dir: Path, content: str) -> None:
        import re
        import subprocess
        from shared_core.agent_provisioner import spawn_subordinate

        # Determine company name if agent belongs to a company
        comp_name = None
        if agent_path.startswith("companies/"):
            parts = agent_path.split("/")
            if len(parts) >= 2:
                comp_name = parts[1]

        # 1. Shell commands: ```action:shell ... ``` or ```bash ... ```
        shell_blocks = re.findall(r"```(?:action:shell|shell|bash)\s*\n(.*?)\n```", content, re.DOTALL)
        for cmd in shell_blocks:
            cmd = cmd.strip()
            if not cmd:
                continue
            workdir = agent_dir
            if comp_name:
                comp_ws = AI_HOLDING_ROOT / "companies" / comp_name / "workspace"
                comp_ws.mkdir(parents=True, exist_ok=True)
                workdir = comp_ws
            
            logger.info(f"[{agent_path}] Executing shell action: {cmd} (in {workdir})")
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(workdir),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                output = (proc.stdout + "\n" + proc.stderr).strip()
                logger.info(f"[{agent_path}] Shell action output: {output[:200]}")
                record_execution_step(
                    step_num=2,
                    agent_path=agent_path,
                    thought=f"Executed command: {cmd}",
                    tool_call=cmd,
                    tool_output=output[:500],
                    memory_snapshot="Shell action executed"
                )
            except Exception as ex:
                logger.error(f"[{agent_path}] Shell execution failed: {ex}")

        # 2. Spawn Department: ```action:spawn_department ... ```
        dept_blocks = re.findall(r"```action:spawn_department\s*\n(.*?)\n```", content, re.DOTALL)
        for block in dept_blocks:
            try:
                data = json.loads(block.strip())
                dept_name = data.get("dept_name")
                if dept_name and comp_name:
                    logger.info(f"[{agent_path}] Spawning department {dept_name} for company {comp_name}")
                    spawn_subordinate(
                        caller_path=agent_path,
                        target_unit_type="department",
                        new_agent_name=dept_name,
                        base_archetype="Dept_Lead_Archetype",
                        company_name=comp_name,
                        initial_task_message=data.get("directive")
                    )
            except Exception as ex:
                logger.error(f"Failed to spawn department: {ex}")

        # 3. Spawn Worker: ```action:spawn_worker ... ```
        worker_blocks = re.findall(r"```action:spawn_worker\s*\n(.*?)\n```", content, re.DOTALL)
        for block in worker_blocks:
            try:
                data = json.loads(block.strip())
                dept_name = data.get("dept_name")
                worker_name = data.get("worker_name")
                if dept_name and worker_name and comp_name:
                    logger.info(f"[{agent_path}] Spawning worker {worker_name} in {dept_name}")
                    spawn_subordinate(
                        caller_path=agent_path,
                        target_unit_type="worker",
                        new_agent_name=worker_name,
                        base_archetype="Worker_Coding_Archetype",
                        company_name=comp_name,
                        dept_name=dept_name,
                        initial_task_message=data.get("directive")
                    )
            except Exception as ex:
                logger.error(f"Failed to spawn worker: {ex}")

    async def run_loop(self) -> None:
        self.running = True
        logger.info("Dispatcher Daemon started. Event-driven Actor loop active (0 MB idle RAM).")
        while self.running:
            try:
                pending = get_pending_messages(limit=10)
                for msg in pending:
                    await self.process_single_message(msg)
            except Exception as e:
                logger.error(f"Dispatcher loop exception: {e}")
            await asyncio.sleep(self.check_interval)

    def stop(self) -> None:
        self.running = False


if __name__ == "__main__":
    daemon = DispatcherDaemon()
    try:
        asyncio.run(daemon.run_loop())
    except KeyboardInterrupt:
        daemon.stop()
        print("Dispatcher stopped.")
