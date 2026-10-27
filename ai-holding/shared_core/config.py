import os
from pathlib import Path

# AI Holding OS Root Directory
# Defaults to local directory if /opt/ai-holding is not writable
DEFAULT_ROOT = Path("/home/manhtien/workspace/AI_agent_company/ai-holding")
if Path("/opt/ai-holding").exists() and os.access("/opt/ai-holding", os.W_OK):
    DEFAULT_ROOT = Path("/opt/ai-holding")

AI_HOLDING_ROOT = Path(os.getenv("AI_HOLDING_ROOT", str(DEFAULT_ROOT))).resolve()

SHARED_CORE_DIR = AI_HOLDING_ROOT / "shared_core"
VAULT_DIR = SHARED_CORE_DIR / "vault"
COMPANIES_DIR = AI_HOLDING_ROOT / "companies"
REGISTRY_DIR = AI_HOLDING_ROOT / "agent_registry"
DEVOPS_DIR = SHARED_CORE_DIR / "devops_ministry"

RESOURCES_DB_PATH = SHARED_CORE_DIR / "resources.db"
MESSAGES_DB_PATH = SHARED_CORE_DIR / "messages.db"
B2B_CONTRACTS_PATH = SHARED_CORE_DIR / "b2b_contracts.json"
GLOBAL_LIMITS_PATH = SHARED_CORE_DIR / "global_limits.json"

MASTER_KEY_PATH = VAULT_DIR / "master.key"
SECRETS_STORE_PATH = VAULT_DIR / "secrets_store.enc"

OMNIROUTE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1")
OMNIROUTE_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key")
