import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from shared_core.config import (
    AI_HOLDING_ROOT,
    COMPANIES_DIR,
    DEVOPS_DIR,
    GLOBAL_LIMITS_PATH,
    REGISTRY_DIR,
)
from shared_core.db_manager import (
    post_message,
    update_agent_runtime_state,
)


class HeadcountExceededError(ValueError):
    """Raised when an agent attempts to spawn subordinates beyond configured limits."""
    pass


class ProvisionerPermissionError(PermissionError):
    """Raised when an unauthorized agent attempts to spawn subordinates."""
    pass


def load_global_limits() -> Dict[str, Any]:
    if GLOBAL_LIMITS_PATH.exists():
        try:
            return json.loads(GLOBAL_LIMITS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "max_departments_per_company": 5,
        "max_workers_per_dept": 6,
        "max_devops_subagents": 10,
        "max_steps_per_task": 30,
        "max_pingpong_turns": 8
    }


def provision_agent(
    target_path: Path,
    base_archetype: str,
    mode: str = "clone",
    custom_soul_directive: Optional[str] = None,
    initial_memory: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates an agent at target_path either by Symlink (--mode shared) or Copy (--mode clone).
    """
    archetype_dir = REGISTRY_DIR / base_archetype
    if not archetype_dir.exists():
        raise FileNotFoundError(f"Archetype '{base_archetype}' not found at {archetype_dir}")

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "shared":
        if target_path.exists() or target_path.is_symlink():
            if target_path.is_symlink():
                target_path.unlink()
            else:
                shutil.rmtree(target_path)
        os.symlink(str(archetype_dir), str(target_path), target_is_directory=True)
        is_link = True
    else:  # clone mode
        if target_path.exists():
            shutil.rmtree(target_path)
        shutil.copytree(str(archetype_dir), str(target_path), symlinks=False)

        # Write custom directives if provided
        if custom_soul_directive:
            soul_file = target_path / "agent_soul.md"
            base_content = soul_file.read_text(encoding="utf-8") if soul_file.exists() else ""
            soul_file.write_text(
                f"{base_content}\n\n## CHỈ THỊ RIÊNG CHO VỊ TRÍ:\n{custom_soul_directive}\n",
                encoding="utf-8"
            )

        if initial_memory:
            (target_path / "agent_memory.md").write_text(initial_memory, encoding="utf-8")

        is_link = False

    try:
        rel_path = str(target_path.relative_to(AI_HOLDING_ROOT))
    except ValueError:
        rel_path = str(target_path)
    update_agent_runtime_state(
        agent_path=rel_path,
        mode="SHARED" if is_link else "CLONED",
        status="IDLE",
        current_step_summary="Agent provisioned successfully"
    )

    return {
        "agent_path": str(target_path),
        "relative_path": rel_path,
        "mode": "SHARED" if is_link else "CLONED",
        "archetype": base_archetype
    }


def unlink_and_clone(agent_target_path: Path) -> Dict[str, Any]:
    """
    Converts a SHARED symlink agent into an independent CLONED agent.
    Safely copies the referenced folder and removes the symlink.
    """
    if not agent_target_path.is_symlink():
        return {
            "status": "ALREADY_CLONED",
            "message": "Target is not a symlink; already an independent clone."
        }

    resolved_path = agent_target_path.resolve()
    agent_target_path.unlink()
    shutil.copytree(str(resolved_path), str(agent_target_path))

    try:
        rel_path = str(agent_target_path.relative_to(AI_HOLDING_ROOT))
    except ValueError:
        rel_path = str(agent_target_path)
    update_agent_runtime_state(
        agent_path=rel_path,
        mode="CLONED",
        status="IDLE",
        current_step_summary="Unlinked from shared archetype and converted to independent clone"
    )

    return {
        "status": "SUCCESS",
        "agent_path": str(agent_target_path),
        "mode": "CLONED",
        "message": "Agent successfully unlinked and cloned into isolated directory."
    }


def spawn_subordinate(
    caller_path: str,
    target_unit_type: str,  # 'company_ceo' | 'department' | 'worker' | 'devops_specialist'
    new_agent_name: str,
    base_archetype: str,
    mode: str = "clone",
    custom_soul_directive: Optional[str] = None,
    initial_task_message: Optional[str] = None,
    company_name: Optional[str] = None,
    dept_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Spawns subordinate agents with hierarchical permission checks and headcount guardrails.
    """
    limits = load_global_limits()
    norm_caller = caller_path.replace("\\", "/").strip("/")

    # 1. Determine target directory based on unit type
    if target_unit_type == "company_ceo":
        if not (norm_caller.startswith("root") or "Chairman" in norm_caller):
            raise ProvisionerPermissionError("Only Chairman/Root Hermes can spawn new Companies and CEOs.")
        if not company_name:
            raise ValueError("company_name is required when creating a company and CEO.")

        comp_dir = COMPANIES_DIR / company_name
        comp_dir.mkdir(parents=True, exist_ok=True)
        (comp_dir / "workspace").mkdir(exist_ok=True)
        (comp_dir / "departments").mkdir(exist_ok=True)

        config_file = comp_dir / "company_config.json"
        if not config_file.exists():
            config_file.write_text(json.dumps({
                "company_name": company_name,
                "status": "ACTIVE",
                "department_count": 0,
                "created_by": caller_path
            }, indent=2), encoding="utf-8")

        target_dir = comp_dir / new_agent_name

    elif target_unit_type == "department":
        # Caller must be CEO
        if "CEO" not in norm_caller:
            raise ProvisionerPermissionError("Only a Company CEO can spawn new Departments.")
        if not company_name:
            # Extract company from caller_path
            parts = Path(caller_path).parts
            if "companies" in parts:
                company_name = parts[parts.index("companies") + 1]
            else:
                raise ValueError("Could not determine company_name from caller_path.")

        comp_dir = COMPANIES_DIR / company_name
        dept_dir = comp_dir / "departments" / new_agent_name
        lead_dir = dept_dir / f"Lead_{new_agent_name.replace('Dept_', '')}"

        # Check department headcount BEFORE creating directories
        existing_depts = [d for d in (comp_dir / "departments").iterdir() if d.is_dir()]
        if len(existing_depts) >= limits.get("max_departments_per_company", 5):
            raise HeadcountExceededError(
                f"Headcount Exceeded: Company {company_name} reached limit of {limits['max_departments_per_company']} departments."
            )

        workers_dir = dept_dir / "workers"
        workers_dir.mkdir(parents=True, exist_ok=True)

        # Save dept_config.json
        (dept_dir / "dept_config.json").write_text(json.dumps({
            "dept_name": new_agent_name,
            "company_name": company_name,
            "worker_count": 0
        }, indent=2), encoding="utf-8")

        target_dir = lead_dir

    elif target_unit_type == "worker":
        # Caller must be Dept_Lead
        if "Lead" not in norm_caller and "CEO" not in norm_caller:
            raise ProvisionerPermissionError("Only a Dept Lead or CEO can spawn Workers.")

        parts = Path(caller_path).parts
        if "departments" in parts:
            dept_idx = parts.index("departments") + 1
            company_idx = parts.index("companies") + 1
            company_name = parts[company_idx]
            dept_name = parts[dept_idx]
        else:
            if not company_name or not dept_name:
                raise ValueError("company_name and dept_name required to spawn worker.")

        workers_dir = COMPANIES_DIR / company_name / "departments" / dept_name / "workers"
        existing_workers = [w for w in workers_dir.iterdir() if w.is_dir() or w.is_symlink()]
        if len(existing_workers) >= limits.get("max_workers_per_dept", 6):
            raise HeadcountExceededError(
                f"Headcount Exceeded: Department {dept_name} reached limit of {limits['max_workers_per_dept']} workers."
            )

        target_dir = workers_dir / new_agent_name

    elif target_unit_type == "devops_specialist":
        if "devops_ministry" not in norm_caller and "root" not in norm_caller:
            raise ProvisionerPermissionError("Only DevOps Hermes or Root can spawn DevOps Specialists.")

        specialists_dir = DEVOPS_DIR / "specialists"
        existing_specs = [s for s in specialists_dir.iterdir() if s.is_dir()]
        if len(existing_specs) >= limits.get("max_devops_subagents", 10):
            raise HeadcountExceededError("Headcount Exceeded: Reached limit of DevOps Specialists.")

        target_dir = specialists_dir / new_agent_name
    else:
        raise ValueError(f"Unknown target_unit_type: {target_unit_type}")

    # 2. Provision the agent folder
    result = provision_agent(
        target_path=target_dir,
        base_archetype=base_archetype,
        mode=mode,
        custom_soul_directive=custom_soul_directive
    )

    # 3. Post initial message if requested
    if initial_task_message:
        post_message(
            sender_path=caller_path,
            receiver_path=result["relative_path"],
            channel_type="DIRECT",
            payload={"task": initial_task_message}
        )

    return result
