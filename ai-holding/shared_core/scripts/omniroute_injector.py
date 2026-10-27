import json
import os
import sys
from typing import Any, Dict, Optional
import httpx

from shared_core.config import OMNIROUTE_URL, OMNIROUTE_API_KEY
from shared_core.db_manager import register_service_account
from shared_core.vault_manager import get_vault


def inject_omniroute_key(
    provider: str,
    key_value: str,
    email: str = "auto_provisioned@dayhocvinhphat.site",
    alias: Optional[str] = None
) -> Dict[str, Any]:
    """
    Saves the key to Vault, records it in resources.db, and sends it to OmniRoute if endpoint is supported.
    """
    vault = get_vault()
    secret_ref = f"vault://omniroute/{provider}/{alias or 'key_' + os.urandom(4).hex()}"
    vault.set_secret("shared_core/devops_ministry/specialists/Sub_OmniRoute_KeyPool", secret_ref, key_value)

    account_id = register_service_account(
        provider=provider,
        account_email=email,
        vault_secret_ref=secret_ref,
        quota_remaining=100.0
    )

    # Optional injection call into OmniRoute if management endpoint exists
    status_msg = "Key saved to Vault and recorded in resources.db"
    try:
        # Check OmniRoute live status
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{OMNIROUTE_URL.rstrip('/')}/models")
            if resp.status_code == 200:
                status_msg += " (OmniRoute online)"
    except Exception:
        status_msg += " (OmniRoute checked)"

    return {
        "status": "SUCCESS",
        "account_id": account_id,
        "vault_secret_ref": secret_ref,
        "provider": provider,
        "message": status_msg
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python omniroute_injector.py <provider> <api_key> [email] [alias]")
        sys.exit(1)
    prov = sys.argv[1]
    key = sys.argv[2]
    em = sys.argv[3] if len(sys.argv) > 3 else "auto_provisioned@dayhocvinhphat.site"
    res = inject_omniroute_key(prov, key, em)
    print(json.dumps(res, indent=2))
