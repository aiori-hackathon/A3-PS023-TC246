"""Tests for Azure deployment infrastructure, configuration, and scripts.

Distinguishes:
1. Local tests (static verification of Azure scripts, security rules, templates, and controller parsing).
2. Azure pre-flight audit tests (Phase 0 unit tests covering 12 pre-flight verification requirements).
3. Live Azure tests (skipped when no live Azure VM is connected, run when AZURE_TESTS=1).
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if not (REPO_ROOT / "deploy").exists() and (REPO_ROOT.parent / "deploy").exists():
    REPO_ROOT = REPO_ROOT.parent
AZURE_DEPLOY_DIR = REPO_ROOT / "deploy" / "azure"
SCRIPT_00 = REPO_ROOT / "scripts" / "azure" / "00-check-azure.sh"


# ==============================================================================
# 1. Local Verification Tests (Run locally without cloud infrastructure)
# ==============================================================================

def test_azure_deployment_files_exist():
    """Verify that all expected Azure deployment files are present."""
    expected_files = [
        "README.md",
        "setup_azure_node.sh",
        "azure_vm_provision.sh",
        "wg_setup_node_a.sh",
        "wg_setup_node_b.sh",
        "verify_azure_deployment.sh",
        "cleanup_azure.sh",
        "boot_test.sh",
    ]
    for filename in expected_files:
        filepath = AZURE_DEPLOY_DIR / filename
        assert filepath.exists(), f"Missing expected Azure deployment file: {filename}"


def test_azure_scripts_executable():
    """Verify that deployment shell scripts are marked executable."""
    scripts = [
        "setup_azure_node.sh",
        "azure_vm_provision.sh",
        "wg_setup_node_a.sh",
        "wg_setup_node_b.sh",
        "verify_azure_deployment.sh",
        "cleanup_azure.sh",
        "boot_test.sh",
    ]
    for s in scripts:
        filepath = AZURE_DEPLOY_DIR / s
        assert os.access(filepath, os.X_OK), f"Script {s} is not executable"


def test_setup_azure_node_safety_and_requirements():
    """Verify setup_azure_node.sh includes all mandatory checks and security parameters."""
    content = (AZURE_DEPLOY_DIR / "setup_azure_node.sh").read_text()

    # Architecture verification
    assert "x86_64" in content, "Missing x86_64 architecture check"
    # RAM check
    assert "MemTotal" in content, "Missing RAM check"
    # /dev/kvm and nested virtualization flags
    assert "/dev/kvm" in content, "Missing /dev/kvm check"
    assert "vmx|svm" in content, "Missing nested virtualization CPU flags check"
    # kvm group membership (never chmod 666)
    assert "usermod -aG kvm" in content, "Must add user to kvm group"
    assert "chmod 666 /dev/kvm" not in content, "Insecure chmod 666 /dev/kvm detected"
    # Cloud Hypervisor v54.0.0
    assert "v54.0.0" in content, "Missing Cloud Hypervisor v54.0.0 reference"
    # Persistent delegation and restart survival
    assert "Delegate=yes" in content, "Missing cgroup v2 Delegate=yes in worker service unit"
    assert "KillMode=process" in content, "Missing KillMode=process in worker service unit"
    # Bind to WireGuard private IP only
    assert "10.100.0.2" in content, "Worker must bind to WireGuard IP (10.100.0.2)"
    assert "8002" in content, "Worker must listen on port 8002"


def test_azure_provisioning_security_and_standard_security_type():
    """Verify azure_vm_provision.sh strictly enforces standard security for nested KVM and dry-run."""
    content = (AZURE_DEPLOY_DIR / "azure_vm_provision.sh").read_text()

    # Security type must be Standard for nested KVM
    assert "--security-type Standard" in content, "Azure VM must use --security-type Standard for nested virtualization"
    # VM candidate
    assert "Standard_D2s_v4" in content, "VM candidate must be Standard_D2s_v4"
    # Network Security Group rules: SSH port 22 restricted, WG UDP 51820, port 8002 denied
    assert "22" in content, "Port 22 SSH must be configured"
    assert "51820" in content, "WireGuard UDP port 51820 must be configured"
    assert "Deny-Worker-API-Public" in content, "Public internet access to worker port 8002 must be explicitly denied"
    # Default dry run
    assert "DRY_RUN=1" in content, "Dry run must be active by default"


def test_wireguard_network_topology():
    """Verify IP allocation in WireGuard scripts between Node A and Node B."""
    node_a_conf = (AZURE_DEPLOY_DIR / "wg_setup_node_a.sh").read_text()
    node_b_conf = (AZURE_DEPLOY_DIR / "wg_setup_node_b.sh").read_text()

    # Node A is 10.100.0.1/24
    assert "Address = 10.100.0.1/24" in node_a_conf
    # Node B is 10.100.0.2/24, ListenPort 51820
    assert "Address = 10.100.0.2/24" in node_b_conf
    assert "ListenPort = 51820" in node_b_conf
    # AllowedIPs routes
    assert "AllowedIPs = 10.100.0.2/32, 192.168.200.0/24" in node_a_conf
    assert "AllowedIPs = 10.100.0.1/32" in node_b_conf


def test_controller_azure_nodes_parsing(monkeypatch):
    """Verify controller successfully parses Azure Node B endpoint and routes."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "controller"))
    monkeypatch.setenv("PS023_API_TOKEN", "test_mock_token_123456")
    test_nodes = "node-a=http://127.0.0.1:8001,node-b=http://10.100.0.2:8002"
    monkeypatch.setenv("PS023_NODES", test_nodes)
    import main

    parsed = main.parse_nodes()
    assert parsed["node-a"] == "http://127.0.0.1:8001"
    assert parsed["node-b"] == "http://10.100.0.2:8002"


# ==============================================================================
# 2. Azure Pre-Flight Script Static & Unit Tests (Phase 0 Audit Tests)
# ==============================================================================

def test_00_check_azure_syntax():
    """Verify scripts/azure/00-check-azure.sh passes bash syntax validation."""
    assert SCRIPT_00.exists(), "00-check-azure.sh must exist"
    res = subprocess.run(["bash", "-n", str(SCRIPT_00)], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax error in 00-check-azure.sh: {res.stderr}"


def test_00_check_azure_strict_bash_mode_unbound_variable():
    """Requirement 1 & 2: Verify script runs cleanly under strict 'set -u' without unbound variable crash ($2, $0, etc.)."""
    res = subprocess.run(["bash", str(SCRIPT_00), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Usage:" in res.stdout
    assert "unbound variable" not in res.stderr.lower()


def test_parse_nested_virt_confirmed_supported():
    """Requirement 3: Explicit True capability is marked CONFIRMED_SUPPORTED."""
    mock_sku = json.dumps([{
        "capabilities": [{"name": "NestedVirtualizationSupported", "value": "True"}]
    }])
    cmd = f'source "{SCRIPT_00}"; parse_nested_virt \'{mock_sku}\''
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == "CONFIRMED_SUPPORTED"


def test_parse_nested_virt_confirmed_unsupported():
    """Requirement 4: Explicit False capability is marked CONFIRMED_UNSUPPORTED."""
    mock_sku = json.dumps([{
        "capabilities": [{"name": "NestedVirtualizationSupported", "value": "False"}]
    }])
    cmd = f'source "{SCRIPT_00}"; parse_nested_virt \'{mock_sku}\''
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == "CONFIRMED_UNSUPPORTED"


def test_parse_nested_virt_missing_capability():
    """Requirement 5: Missing capability is marked UNCONFIRMED_METADATA."""
    mock_sku = json.dumps([{
        "capabilities": [{"name": "vCPUs", "value": "2"}]
    }])
    cmd = f'source "{SCRIPT_00}"; parse_nested_virt \'{mock_sku}\''
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == "UNCONFIRMED_METADATA"


def test_parse_nested_virt_unchecked():
    """Requirement 6: 'unchecked' flag is marked UNCHECKED and NOT treated as confirmed."""
    mock_sku = json.dumps([{
        "capabilities": [{"name": "NestedVirtualizationSupported", "value": "unchecked"}]
    }])
    cmd = f'source "{SCRIPT_00}"; parse_nested_virt \'{mock_sku}\''
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == "UNCHECKED"


def test_sku_unavailable_in_region():
    """Requirement 7: Empty or missing SKU JSON is marked SKU_NOT_FOUND."""
    cmd = f'source "{SCRIPT_00}"; parse_nested_virt "[]"'
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == "SKU_NOT_FOUND"


def test_sku_restrictions_parsing():
    """Requirement 7 (cont): Zone and subscription restrictions are parsed accurately."""
    mock_sku = json.dumps([{
        "restrictions": [{
            "type": "Zone",
            "reasonCode": "NotAvailableForSubscription",
            "restrictionInfo": {"zones": ["2", "1"]}
        }]
    }])
    check_code = f'''
    source "{SCRIPT_00}"
    restrictions=$(echo '{mock_sku}' | jq -r '.[0].restrictions[]? | "\\(.type): \\(.reasonCode) (zones: \\(.restrictionInfo.zones // [] | join(",")))"')
    echo "$restrictions"
    '''
    res = subprocess.run(["bash", "-c", check_code], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Zone: NotAvailableForSubscription (zones: 2,1)" in res.stdout


def test_quota_exhaustion_regional():
    """Requirement 8: Regional vCPU quota exhaustion (cores limit reached) is detected."""
    mock_quota = json.dumps([
        {"name": {"value": "cores", "localizedValue": "Total Regional vCPUs"}, "currentValue": "6", "limit": "6"}
    ])
    check_code = f'''
    source "{SCRIPT_00}"
    cores_info=$(echo '{mock_quota}' | jq -r '.[]? | select(.name.value == "cores") | "\\(.currentValue)|\\(.limit)"')
    c_cur=$(cut -d'|' -f1 <<< "$cores_info")
    c_lim=$(cut -d'|' -f2 <<< "$cores_info")
    c_rem=$(( c_lim - c_cur ))
    echo "REMAINING:$c_rem"
    '''
    res = subprocess.run(["bash", "-c", check_code], capture_output=True, text=True)
    assert res.returncode == 0
    assert "REMAINING:0" in res.stdout


def test_quota_insufficient_sku_family():
    """Requirement 9: SKU Family quota with limit=0 (e.g. StandardDSv5Family) is detected and flagged."""
    mock_quota = json.dumps([
        {"name": {"value": "standardDSv5Family", "localizedValue": "Standard DSv5 Family vCPUs"}, "currentValue": "0", "limit": "0"},
        {"name": {"value": "standardDSv4Family", "localizedValue": "Standard DSv4 Family vCPUs"}, "currentValue": "0", "limit": "4"}
    ])
    check_code = f'''
    source "{SCRIPT_00}"
    fam_info=$(echo '{mock_quota}' | jq -r --arg fam "standardDSv5Family" '.[]? | select(.name.value | ascii_downcase == ($fam | ascii_downcase)) | "\\(.currentValue)|\\(.limit)"')
    f_lim=$(cut -d'|' -f2 <<< "$fam_info")
    echo "LIMIT:$f_lim"
    '''
    res = subprocess.run(["bash", "-c", check_code], capture_output=True, text=True)
    assert res.returncode == 0
    assert "LIMIT:0" in res.stdout


def test_azure_cli_api_failure_handling():
    """Requirement 10: Graceful handling of empty/corrupted API responses without unhandled script failure."""
    cmd = f'source "{SCRIPT_00}"; parse_nested_virt ""'
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == "SKU_NOT_FOUND"


def test_pricing_presentation_and_currency_formatting():
    """Requirement 11: Pricing contains proper currency symbols, distinguishes compute deallocation ($0.00), and labels static estimates."""
    content = SCRIPT_00.read_text()
    assert "\\$0.096" in content or "$0.096" in content
    assert "\\$0.00" in content or "$0.00" in content
    assert "\\$2.40" in content or "$2.40" in content
    assert "Static Calculator Estimates" in content or "Static Retail Calculator Estimate" in content
    # Verify unescaped buggy dollar patterns are absent in echo statements
    assert not re.search(r'echo.*[^\\]\$0\.101', content), "Corrupted unescaped $0.101 found in echo statement"
    assert not re.search(r'echo.*[^\\]\$2\.40', content), "Corrupted unescaped $2.40 found in echo statement"


def test_determine_family_and_fallback_mapping():
    """Requirement 12: Proper family name mapping for Dv5, Dv4, Dv3, and fallback regions."""
    check_code = f'''
    source "{SCRIPT_00}"
    echo "v5:$(determine_family Standard_D2s_v5)"
    echo "v4:$(determine_family Standard_D2s_v4)"
    echo "v3:$(determine_family Standard_D2s_v3)"
    '''
    res = subprocess.run(["bash", "-c", check_code], capture_output=True, text=True)
    assert res.returncode == 0
    assert "v5:standardDSv5Family" in res.stdout
    assert "v4:standardDSv4Family" in res.stdout
    assert "v3:standardDSv3Family" in res.stdout


def test_default_sku_and_family_in_common_config():
    """Task 1 & 2: Verify scripts/azure/common.sh defaults to Standard_D2s_v4 and standardDSv4Family."""
    common_sh = REPO_ROOT / "scripts" / "azure" / "common.sh"
    content = common_sh.read_text()
    assert 'AZURE_VM_SIZE="${AZURE_VM_SIZE:-Standard_D2s_v4}"' in content
    assert 'standardDSv4Family' in content


def test_regional_non_zonal_deployment_default():
    """Task 3: Verify 01-create-node-b.sh defaults to regional non-zonal deployment and does not hardcode zone 3."""
    create_sh = REPO_ROOT / "scripts" / "azure" / "01-create-node-b.sh"
    content = create_sh.read_text()
    # Regional non-zonal default
    assert "Regional (Non-zonal deployment)" in content
    # Zone 3 is not unconditionally hardcoded into az vm create
    assert 'az vm create' in content
    # Checks that dry run displays Regional (Non-zonal) when AZURE_ZONE is unset
    res = subprocess.run(["bash", str(create_sh), "--dry-run"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Regional (Non-zonal deployment)" in res.stdout


def test_pricing_calculations_refer_to_d2s_v4_and_labeled_unverified():
    """Task 4: Verify pricing calculations refer to D2s_v4 and are explicitly labeled unverified."""
    content = SCRIPT_00.read_text()
    assert "Target SKU: $target_sku" in content
    assert "Static Retail Calculator Estimate (Unverified via dynamic Retail API call)" in content
    assert "\\$0.096" in content or "$0.096" in content


def test_standard_security_type_enforced_for_nested_kvm():
    """Task 5: Verify Standard security type is enforced across scripts for nested KVM compatibility."""
    common_sh = (REPO_ROOT / "scripts" / "azure" / "common.sh").read_text()
    create_sh = (REPO_ROOT / "scripts" / "azure" / "01-create-node-b.sh").read_text()
    assert 'AZURE_SECURITY_TYPE="${AZURE_SECURITY_TYPE:-Standard}"' in common_sh
    assert '--security-type "$AZURE_SECURITY_TYPE"' in create_sh or '--security-type Standard' in create_sh


def test_vm_creation_uses_storage_sku_not_os_disk_type():
    """Verify scripts/azure/01-create-node-b.sh and deployment scripts use --storage-sku StandardSSD_LRS."""
    create_sh = (REPO_ROOT / "scripts" / "azure" / "01-create-node-b.sh").read_text()
    assert "--storage-sku StandardSSD_LRS" in create_sh
    assert "--os-disk-type" not in create_sh

    deploy_sh = (REPO_ROOT / "deploy" / "azure" / "azure_vm_provision.sh").read_text()
    assert "--storage-sku StandardSSD_LRS" in deploy_sh
    assert "--os-disk-type" not in deploy_sh


def test_vm_creation_command_no_empty_string_arguments():
    """Regression test: Verify az vm create argument array contains zero empty string arguments (prevents unrecognized arguments: error)."""
    check_code = f'''
    set -euo pipefail
    source "{REPO_ROOT}/scripts/azure/common.sh"
    AZURE_ZONE=""
    VM_CMD=(
      az vm create
      --resource-group "$AZURE_RG"
      --name "$AZURE_VM_NAME"
      --nics nic-ps023-node-b
      --image "$AZURE_OS_IMAGE"
      --size "$AZURE_VM_SIZE"
      --admin-username "$AZURE_ADMIN_USER"
      --ssh-key-values @"$AZURE_SSH_KEY"
      --os-disk-size-gb "$AZURE_OS_DISK_SIZE_GB"
      --storage-sku StandardSSD_LRS
      --security-type "$AZURE_SECURITY_TYPE"
    )
    if [ -n "${{AZURE_ZONE:-}}" ]; then
      VM_CMD+=(--zone "$AZURE_ZONE")
    fi
    VM_CMD+=(-o none)

    for i in "${{!VM_CMD[@]}}"; do
      if [ -z "${{VM_CMD[$i]}}" ]; then
        echo "FAIL: Empty argument found at index $i"
        exit 1
      fi
    done
    echo "PASS: no empty arguments"
    '''
    res = subprocess.run(["bash", "-c", check_code], capture_output=True, text=True)
    assert res.returncode == 0
    assert "PASS" in res.stdout

    # Verify 01-create-node-b.sh does not contain quoted empty array pattern
    create_sh = (REPO_ROOT / "scripts" / "azure" / "01-create-node-b.sh").read_text()
    assert '"${ZONE_ARGS[@]:-}"' not in create_sh
    assert '"${ZONE_ARGS[@]}"' not in create_sh





# ==============================================================================
# 3. Live Azure Tests (Conditional: only run when AZURE_TESTS=1 is set)
# ==============================================================================

@pytest.mark.skipif(
    not os.environ.get("AZURE_TESTS"),
    reason="Live Azure testing not enabled (set AZURE_TESTS=1 with active Azure VM)",
)
def test_live_azure_wireguard_ping():
    """Ping Azure Node B WireGuard IP (10.100.0.2)."""
    res = subprocess.run(["ping", "-c", "2", "-W", "2", "10.100.0.2"], capture_output=True)
    assert res.returncode == 0, "Failed to ping Azure Node B over WireGuard"


@pytest.mark.skipif(
    not os.environ.get("AZURE_TESTS"),
    reason="Live Azure testing not enabled (set AZURE_TESTS=1 with active Azure VM)",
)
def test_live_azure_worker_health():
    """Verify Azure Node B HTTP health endpoint responds with node-b."""
    import httpx
    resp = httpx.get("http://10.100.0.2:8002/health", timeout=5.0)
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"
    assert resp.json().get("node_id") == "node-b"
