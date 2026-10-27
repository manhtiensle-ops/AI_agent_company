import json
import os
import shutil
import tempfile
from pathlib import Path
import pytest

from shared_core.agent_provisioner import (
    HeadcountExceededError,
    ProvisionerPermissionError,
    provision_agent,
    spawn_subordinate,
    unlink_and_clone,
)
from shared_core.db_manager import (
    acquire_resource_lock,
    init_databases,
    record_execution_step,
    register_service_account,
    release_resource_lock,
    rollback_execution_steps,
)
from shared_core.rbac_router import validate_communication_permission
from shared_core.vault_manager import VaultManager, ZeroTrustSecurityError


@pytest.fixture(autouse=True)
def setup_test_databases():
    init_databases()
    # Clean up test company Test_Company_X if exists
    from shared_core.config import COMPANIES_DIR, RESOURCES_DB_PATH
    from shared_core.db_manager import get_db_connection
    test_comp = COMPANIES_DIR / "Test_Company_X"
    if test_comp.exists():
        shutil.rmtree(test_comp)
    with get_db_connection(RESOURCES_DB_PATH) as conn:
        conn.execute("DELETE FROM service_accounts WHERE provider = 'test_prov'")
        conn.commit()


def test_vault_zero_trust():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        mkey = tmp_path / "master.key"
        sstore = tmp_path / "secrets.enc"
        vault = VaultManager(master_key_path=mkey, store_path=sstore)

        # 1. DevOps identity has access
        vault.set_secret(
            caller_path="shared_core/devops_ministry/My_credential_devops_hermes",
            secret_ref="vault://test/token",
            secret_value="SEC_12345"
        )
        val = vault.get_secret(
            caller_path="shared_core/devops_ministry/specialists/Sub_Database_Provisioner",
            secret_ref="vault://test/token"
        )
        assert val == "SEC_12345"

        # 2. Non-DevOps identity is blocked by Zero-Trust
        with pytest.raises(ZeroTrustSecurityError):
            vault.get_secret(
                caller_path="companies/Company_A_Bakery/CEO",
                secret_ref="vault://test/token"
            )


def test_resources_atomic_locking():
    # Register a new service account
    acc_id = register_service_account(
        provider="test_prov",
        account_email="tester@dayhocvinhphat.site",
        vault_secret_ref="vault://test_prov/key_01"
    )
    assert acc_id > 0

    # Agent 1 locks the account
    lock1 = acquire_resource_lock("test_prov", "Company_A", "Agent_1")
    assert lock1 is not None
    assert lock1["locked_by_agent"] == "Agent_1"

    # Agent 2 tries to acquire when none available
    lock2 = acquire_resource_lock("test_prov", "Company_B", "Agent_2")
    assert lock2 is None

    # Agent 1 releases the lock
    released = release_resource_lock(lock1["id"], "Agent_1")
    assert released is True

    # Now Agent 2 can acquire it
    lock2_again = acquire_resource_lock("test_prov", "Company_B", "Agent_2")
    assert lock2_again is not None
    assert lock2_again["locked_by_agent"] == "Agent_2"
    release_resource_lock(lock2_again["id"], "Agent_2")


def test_agent_provisioning_and_headcount():
    # 1. Spawn a test company and CEO
    ceo_res = spawn_subordinate(
        caller_path="Chairman/Root_Hermes",
        target_unit_type="company_ceo",
        new_agent_name="CEO",
        base_archetype="CEO_Archetype",
        company_name="Test_Company_X"
    )
    assert Path(ceo_res["agent_path"]).exists()

    # 2. Spawn 5 departments (max allowed)
    for i in range(1, 6):
        d_res = spawn_subordinate(
            caller_path="companies/Test_Company_X/CEO",
            target_unit_type="department",
            new_agent_name=f"Dept_{i}",
            base_archetype="Dept_Lead_Archetype",
            company_name="Test_Company_X"
        )
        assert Path(d_res["agent_path"]).exists()

    # 3. 6th department must raise HeadcountExceededError
    with pytest.raises(HeadcountExceededError):
        spawn_subordinate(
            caller_path="companies/Test_Company_X/CEO",
            target_unit_type="department",
            new_agent_name="Dept_6",
            base_archetype="Dept_Lead_Archetype",
            company_name="Test_Company_X"
        )


def test_unlink_and_clone():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        target = tmp_path / "worker_test"

        # Provision as SHARED (symlink)
        res = provision_agent(target_path=target, base_archetype="Worker_Coding_Archetype", mode="shared")
        assert target.is_symlink()

        # Unlink & Clone
        unlink_res = unlink_and_clone(target)
        assert unlink_res["status"] == "SUCCESS"
        assert not target.is_symlink()
        assert target.is_dir()
        assert (target / "agent_soul.md").exists()


def test_rbac_firewall_and_b2b():
    # Inter-company CEO communication without active contract
    allowed, reason = validate_communication_permission(
        sender_path="companies/Comp1/CEO",
        receiver_path="companies/Comp2/CEO",
        channel_type="B2B_BRIDGE"
    )
    assert not allowed
    assert "B2B Firewall" in (reason or "")

    # Intra-company CEO to Dept Lead
    allowed_internal, _ = validate_communication_permission(
        sender_path="companies/Comp1/CEO",
        receiver_path="companies/Comp1/departments/Dept1/Lead",
        channel_type="DIRECT"
    )
    assert allowed_internal is True


def test_execution_steps_and_rollback():
    agent_path = "test_agent_for_rollback"
    record_execution_step(1, agent_path, "Thought 1", "tool_1", "out_1", "Snapshot Memory 1")
    record_execution_step(2, agent_path, "Thought 2", "tool_2", "out_2", "Snapshot Memory 2")
    record_execution_step(3, agent_path, "Thought 3", "tool_3", "out_3", "Snapshot Memory 3")

    # Rollback to step 1
    snapshot = rollback_execution_steps(agent_path, target_step_num=1)
    assert snapshot == "Snapshot Memory 1"
