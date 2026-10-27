import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared_core.config import B2B_CONTRACTS_PATH, COMPANIES_DIR, GLOBAL_LIMITS_PATH
from shared_core.db_manager import get_db_connection, MESSAGES_DB_PATH


class PermissionDeniedError(PermissionError):
    pass


def load_b2b_contracts() -> List[Dict[str, Any]]:
    if B2B_CONTRACTS_PATH.exists():
        try:
            data = json.loads(B2B_CONTRACTS_PATH.read_text(encoding="utf-8"))
            return data.get("contracts", [])
        except Exception:
            pass
    return []


def is_b2b_contract_active(company_1: str, company_2: str, sender: str, receiver: str) -> bool:
    contracts = load_b2b_contracts()
    for c in contracts:
        if c.get("status") == "ACTIVE":
            parties = [c.get("company_1"), c.get("company_2")]
            if company_1 in parties and company_2 in parties:
                allowed_reps = c.get("allowed_representatives", [])
                if not allowed_reps or (any(r in sender for r in allowed_reps) and any(r in receiver for r in allowed_reps)):
                    return True
    return False


def get_conversation_turns(sender: str, receiver: str, channel_type: str) -> int:
    """Calculates recent conversation turns between two agents to prevent infinite ping-pong loops."""
    try:
        with get_db_connection(MESSAGES_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM messages
                WHERE channel_type = ? AND (
                    (sender_path = ? AND receiver_path = ?) OR
                    (sender_path = ? AND receiver_path = ?)
                )
                AND created_at >= datetime('now', '-30 minutes')
            """, (channel_type, sender, receiver, receiver, sender))
            row = cursor.fetchone()
            return row["cnt"] if row else 0
    except Exception:
        return 0


def validate_communication_permission(
    sender_path: str,
    receiver_path: str,
    channel_type: str
) -> Tuple[bool, Optional[str]]:
    """
    RBAC verification according to AI Holding Company-as-Code axioms:
    - Vertical: Chairman <-> CEO <-> Dept_Lead <-> Worker
    - Horizontal internal: Worker <-> Worker in same department, Dept_Lead <-> Dept_Lead in same company
    - Infrastructure: CEO / Dept_Lead -> DevOps Hermes -> Specialists
    - B2B Bridge: CEO_A <-> CEO_B: blocked unless authorized by Chairman in b2b_contracts.json.
    - Ping-Pong Loop Protection: max 8 turns between peers.
    """
    s = sender_path.replace("\\", "/").strip("/")
    r = receiver_path.replace("\\", "/").strip("/")

    # Chairman has unrestricted universal access
    if "root" in s or "Chairman" in s or "root" in r or "Chairman" in r:
        return True, None

    # Infrastructure Tickets
    if "devops_ministry" in r or "My_credential_devops_hermes" in r:
        return True, None
    if "devops_ministry" in s:
        # DevOps communicating with sub-specialists or reporting back to caller
        return True, None

    # Ping-Pong Loop Guardrail
    turns = get_conversation_turns(s, r, channel_type)
    if turns >= 8:
        return False, f"Ping-Pong Loop Protection: Max turns (8) reached between '{s}' and '{r}'. Must finalize solution or escalate to Chairman."

    # Parse company, department, role
    s_parts = s.split("/")
    r_parts = r.split("/")

    s_company = s_parts[s_parts.index("companies") + 1] if "companies" in s_parts else None
    r_company = r_parts[r_parts.index("companies") + 1] if "companies" in r_parts else None

    # Inter-company communication (B2B Bridge)
    if s_company and r_company and s_company != r_company:
        if not ("CEO" in s and "CEO" in r):
            return False, f"Permission Denied: Only CEOs can negotiate B2B. '{s}' and '{r}' cannot communicate directly."
        if not is_b2b_contract_active(s_company, r_company, s, r):
            return False, f"B2B Firewall: No ACTIVE B2B contract between '{s_company}' and '{r_company}'. Requires Chairman approval."
        return True, None

    # Same company communication
    if s_company and r_company and s_company == r_company:
        # CEO <-> Dept_Lead
        if ("CEO" in s and "Lead" in r) or ("Lead" in s and "CEO" in r):
            return True, None

        # Dept_Lead <-> Dept_Lead in same company
        if "Lead" in s and "Lead" in r:
            return True, None

        # Dept_Lead <-> Worker
        s_dept = s_parts[s_parts.index("departments") + 1] if "departments" in s_parts else None
        r_dept = r_parts[r_parts.index("departments") + 1] if "departments" in r_parts else None

        if s_dept and r_dept and s_dept == r_dept:
            # Within same department: Lead <-> Worker or Worker <-> Worker
            return True, None

        # Cross-department worker communication is prohibited without Dept_Lead coordination
        if "Worker" in s and "Worker" in r and s_dept != r_dept:
            return False, f"Cross-Department Violation: Workers across different departments ('{s_dept}' and '{r_dept}') cannot chat directly. Coordinate via Dept_Leads."

    return True, None
