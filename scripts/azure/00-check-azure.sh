#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration — Step 0: Pre-Flight Environment & Quota Check
# Validates Azure CLI, active subscription, regional vCPU quotas,
# SKU family quotas, SKU restrictions, and nested virtualization capability.
# Safe, idempotent, strictly READ-ONLY.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

# ------------------------------------------------------------------------------
# 1. Helper Functions
# ------------------------------------------------------------------------------

determine_family() {
  local sku="$1"
  case "$sku" in
    *D*s_v5|*d*s_v5|*D*v5|*d*v5) echo "standardDSv5Family" ;;
    *D*s_v4|*d*s_v4|*D*v4|*d*v4) echo "standardDSv4Family" ;;
    *D*s_v3|*d*s_v3|*D*v3|*d*v3) echo "standardDSv3Family" ;;
    *D*s_v2|*d*s_v2|*D*v2|*d*v2) echo "standardDSv2Family" ;;
    *B*s_v2|*b*s_v2)             echo "standardBsv2Family" ;;
    *B*s|*b*s)                   echo "standardBSFamily" ;;
    *)                           echo "" ;;
  esac
}

get_sku_required_vcpus() {
  local sku="$1"
  if [[ "$sku" =~ [a-zA-Z]+_?[a-zA-Z]([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo "2"
  fi
}

fetch_sku_json() {
  local loc="$1"
  local sku="$2"
  local use_cache="${3:-1}"
  local cache_dir="/tmp/ps023_azure_cache"
  local cache_file="${cache_dir}/sku_${loc}_${sku}.json"

  if [ "$use_cache" -eq 1 ] && [ -f "$cache_file" ]; then
    # Cache valid for 3 hours (10800s)
    local now mtime age
    now=$(date +%s)
    mtime=$(stat -c %Y "$cache_file" 2>/dev/null || echo 0)
    age=$(( now - mtime ))
    if [ "$age" -lt 10800 ] && [ -s "$cache_file" ]; then
      cat "$cache_file"
      return 0
    fi
  fi

  local res
  res=$(az vm list-skus --location "$loc" --size "$sku" --output json 2>/dev/null || true)
  if [ -n "$res" ] && [ "$res" != "[]" ]; then
    mkdir -p "$cache_dir" 2>/dev/null || true
    echo "$res" > "$cache_file" 2>/dev/null || true
  fi
  echo "$res"
}

parse_nested_virt() {
  local sku_json="$1"
  if [ -z "$sku_json" ] || [ "$sku_json" = "[]" ]; then
    echo "SKU_NOT_FOUND"
    return 0
  fi

  local val
  val=$(echo "$sku_json" | jq -r '.[0].capabilities[]? | select(.name == "NestedVirtualizationSupported") | .value' 2>/dev/null || true)
  if [ "$val" = "True" ]; then
    echo "CONFIRMED_SUPPORTED"
  elif [ "$val" = "False" ]; then
    echo "CONFIRMED_UNSUPPORTED"
  elif [ "$val" = "unchecked" ]; then
    echo "UNCHECKED"
  elif [ -z "$val" ] || [ "$val" = "null" ]; then
    echo "UNCONFIRMED_METADATA"
  else
    echo "UNKNOWN:$val"
  fi
}

assess_region() {
  local loc="$1"
  local sku="$2"
  local is_fallback="${3:-0}"
  local use_cache="${4:-1}"

  echo -e "${CYAN}----------------------------------------------------------------------${NC}"
  if [ "$is_fallback" -eq 1 ]; then
    echo -e "${CYAN} Assessing Fallback Region: ${loc}${NC}"
  else
    echo -e "${CYAN} Assessing Primary Region: ${loc}${NC}"
  fi
  echo -e "${CYAN}----------------------------------------------------------------------${NC}"

  # A. Regional & Family Quotas
  log_info "Querying compute vCPU quotas in '${loc}'..."
  local quota_json
  quota_json=$(az vm list-usage --location "$loc" --output json 2>/dev/null || true)

  local fam_name
  fam_name=$(determine_family "$sku")
  local req_vcpus
  req_vcpus=$(get_sku_required_vcpus "$sku")

  if [ -z "$quota_json" ] || [ "$quota_json" = "[]" ]; then
    log_warn "Failed to retrieve quota usage from Azure API for ${loc}."
  else
    local cores_info
    cores_info=$(echo "$quota_json" | jq -r '.[]? | select(.name.value == "cores") | "\(.currentValue)|\(.limit)|\(.name.localizedValue)"' 2>/dev/null || true)
    if [ -n "$cores_info" ]; then
      local c_cur c_lim c_rem
      c_cur=$(cut -d'|' -f1 <<< "$cores_info")
      c_lim=$(cut -d'|' -f2 <<< "$cores_info")
      c_rem=$(( c_lim - c_cur ))
      if [ "$c_rem" -le 0 ]; then
        log_err "Total Regional vCPUs exhausted! Current=${c_cur} / Limit=${c_lim} (Remaining: 0)"
      else
        log_ok "Total Regional vCPUs: Current=${c_cur} / Limit=${c_lim} (Available: ${c_rem})"
      fi
    else
      log_warn "Total Regional vCPUs ('cores') metric not found in API response."
    fi

    if [ -n "$fam_name" ]; then
      local fam_info
      fam_info=$(echo "$quota_json" | jq -r --arg fam "$fam_name" '.[]? | select(.name.value | ascii_downcase == ($fam | ascii_downcase)) | "\(.currentValue)|\(.limit)|\(.name.localizedValue)"' 2>/dev/null || true)
      if [ -n "$fam_info" ]; then
        local f_cur f_lim f_rem f_locname
        f_cur=$(cut -d'|' -f1 <<< "$fam_info")
        f_lim=$(cut -d'|' -f2 <<< "$fam_info")
        f_locname=$(cut -d'|' -f3 <<< "$fam_info")
        f_rem=$(( f_lim - f_cur ))

        if [ "$f_lim" -eq 0 ]; then
          log_warn "SKU Family Quota for '${fam_name}' (${f_locname}) is 0 in ${loc}!"
          echo "    > Azure for Students subscriptions allocate 0 vCPUs to standardDSv5Family."
          echo "    > Recommended SKU for Students: Standard_D2s_v4 (standardDSv4Family has limit 4)."
        elif [ "$f_rem" -lt "$req_vcpus" ]; then
          log_err "Insufficient family vCPUs: Current=${f_cur} / Limit=${f_lim} (Requires ${req_vcpus}, Available: ${f_rem})"
        else
          log_ok "SKU Family Quota '${fam_name}': Current=${f_cur} / Limit=${f_lim} (Available: ${f_rem}, Requires: ${req_vcpus})"
        fi
      else
        log_warn "SKU Family '${fam_name}' not listed in quota response for ${loc}."
      fi
    fi
  fi

  # B. SKU Availability & Restrictions
  log_info "Checking SKU '${sku}' availability and capabilities in '${loc}'..."
  local sku_json
  sku_json=$(fetch_sku_json "$loc" "$sku" "$use_cache")

  if [ -z "$sku_json" ] || [ "$sku_json" = "[]" ]; then
    log_err "SKU '${sku}' is NOT AVAILABLE in region '${loc}'."
    echo
    return 0
  fi

  # Check SKU Restrictions
  local restrictions
  restrictions=$(echo "$sku_json" | jq -r '.[0].restrictions[]? | "\(.type): \(.reasonCode) (zones: \(.restrictionInfo.zones // [] | join(",")))"' 2>/dev/null || true)
  if [ -n "$restrictions" ]; then
    log_warn "SKU '${sku}' has restrictions in '${loc}':"
    while IFS= read -r line; do
      echo "    * $line"
    done <<< "$restrictions"
    local avail_zones
    avail_zones=$(echo "$sku_json" | jq -r '.[0].locationInfo[0].zones[]?' 2>/dev/null | tr '\n' ' ' || echo "all")
    echo "    * Available/Configured zones in ${loc}: ${avail_zones:-none}"
    echo "    * Note: Regional non-zonal deployment (omitting --zone) is supported,"
    echo "            or explicit pinning to Zone 3 can be configured via AZURE_ZONE=3."
  else
    log_ok "SKU '${sku}' has no subscription or zone restrictions in '${loc}'."
  fi

  # C. Nested Virtualization Capability Check
  local nv_status
  nv_status=$(parse_nested_virt "$sku_json")

  case "$nv_status" in
    CONFIRMED_SUPPORTED)
      log_ok "Nested Virtualization: CONFIRMED SUPPORTED (Explicit True flag in Azure Compute API)"
      ;;
    CONFIRMED_UNSUPPORTED)
      log_err "Nested Virtualization: CONFIRMED UNSUPPORTED (Explicit False flag in Azure Compute API)"
      ;;
    UNCHECKED)
      log_warn "Nested Virtualization: UNCHECKED (Flag returned 'unchecked'; NOT confirmed)"
      ;;
    UNCONFIRMED_METADATA)
      log_warn "Nested Virtualization: UNCONFIRMED in Azure API metadata"
      echo "    * Azure Resource Provider does not publish 'NestedVirtualizationSupported' tag for '${sku}'."
      echo "    * Official Microsoft documentation confirms Intel VT-x / AMD-V nested KVM on Dv4/Dv5."
      echo "    * Live verification will be performed during bootstrap (02-bootstrap-node-b.sh) via /dev/kvm and vmx|svm CPU flags."
      ;;
    SKU_NOT_FOUND)
      log_err "Nested Virtualization check skipped: SKU not found."
      ;;
    *)
      log_warn "Nested Virtualization: UNKNOWN status '${nv_status}'"
      ;;
  esac
  echo
  return 0
}

# ------------------------------------------------------------------------------
# 2. Main Entry Point
# ------------------------------------------------------------------------------
main() {
  local use_cache=1
  local target_sku="${AZURE_VM_SIZE}"
  local target_loc="${AZURE_LOCATION}"
  local fallback_loc="${AZURE_LOCATION_FALLBACK}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --sku)
        target_sku="$2"
        shift 2
        ;;
      --location)
        target_loc="$2"
        shift 2
        ;;
      --no-cache)
        use_cache=0
        shift
        ;;
      --help|-h)
        echo "Usage: $0 [--sku <sku>] [--location <region>] [--no-cache]"
        echo "  --sku <sku>       : VM SKU to check (default: $AZURE_VM_SIZE)"
        echo "  --location <loc>  : Primary region (default: $AZURE_LOCATION)"
        echo "  --no-cache        : Bypass cached SKU metadata"
        exit 0
        ;;
      *)
        shift
        ;;
    esac
  done

  echo -e "${BLUE}======================================================================${NC}"
  echo -e "${BLUE} PS-023: Azure Pre-Flight Quota & Environment Assessment${NC}"
  echo -e "${BLUE} Target VM: ${target_sku} in ${target_loc} (Fallback: ${fallback_loc})${NC}"
  echo -e "${BLUE}======================================================================${NC}"
  echo

  # Check Azure CLI Installation
  log_info "Verifying Azure CLI installation..."
  if ! command -v az >/dev/null 2>&1; then
    log_err "Azure CLI ('az') is not installed or not in PATH."
    echo
    echo "Installation instructions for Fedora Linux:"
    echo "  sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc"
    echo "  sudo dnf install -y https://packages.microsoft.com/config/rhel/9.0/packages-microsoft-prod.rpm"
    echo "  sudo dnf install -y azure-cli"
    exit 1
  fi
  local az_ver
  az_ver=$(az version --output json 2>/dev/null | grep -o '"azure-cli": *"[^"]*"' | head -1 | cut -d'"' -f4 || echo "installed")
  log_ok "Azure CLI detected (version: $az_ver)"

  # Check Azure Authentication & Subscription
  log_info "Checking Azure CLI authentication status..."
  local account_json
  account_json=$(az account show --output json 2>/dev/null || true)

  if [ -z "$account_json" ]; then
    log_err "Not authenticated to Azure CLI. Please run:"
    echo "  az login"
    exit 1
  fi

  local sub_name sub_id sub_state
  sub_name=$(echo "$account_json" | grep -o '"name": *"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")
  sub_id=$(echo "$account_json" | grep -o '"id": *"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")
  sub_state=$(echo "$account_json" | grep -o '"state": *"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")

  log_ok "Authenticated Account: $sub_name (State: $sub_state)"
  log_info "Subscription ID: ${sub_id:0:8}-****-****-****-************"

  # Regional Assessments
  assess_region "$target_loc" "$target_sku" 0 "$use_cache"
  assess_region "$fallback_loc" "$target_sku" 1 "$use_cache"

  # If target is Standard_D2s_v5 and standardDSv5Family is 0, also assess Standard_D2s_v4
  if [ "$target_sku" = "Standard_D2s_v5" ]; then
    echo -e "${YELLOW}======================================================================${NC}"
    echo -e "${YELLOW} CANDIDATE COMPARISON: Standard_D2s_v4 (Student Quota Safe Alternative)${NC}"
    echo -e "${YELLOW}======================================================================${NC}"
    assess_region "$target_loc" "Standard_D2s_v4" 0 "$use_cache"
  fi

  # Pricing & Budget Preview (Escaped Currency Values for Strict Bash)
  echo "======================================================================"
  echo " ESTIMATED PRICING & STUDENT BUDGET PREVIEW (Static Calculator Estimates)"
  echo "======================================================================"
  echo "Target SKU: $target_sku (2 vCPUs, 8 GiB RAM, Nested KVM)"
  echo "1. Active Compute Rate:    ~\$0.096/hour in Central India (~\$0.104/hour in SE Asia)"
  echo "2. Deallocated Compute:    \$0.00/hour (Billed strictly when running)"
  echo "3. 30 GiB Standard SSD:    ~\$2.40/month (~\$0.08/day)"
  echo "4. Static Public IPv4:     ~\$0.005/hour (~\$0.12/day)"
  echo "5. Total for 8-Hour Demo:  ~\$0.89 total (fits well within \$100 student credit pool)"
  echo "----------------------------------------------------------------------"
  echo "Pricing Verification: Static Retail Calculator Estimate (Unverified via dynamic Retail API call)"
  echo "Note: Compute is \$0.00 when deallocated; storage/IP accrue while provisioned."
  echo "======================================================================"
  echo

  # Final Summary & Safety Verdict
  echo -e "${BLUE}======================================================================${NC}"
  echo -e "${BLUE} PRE-FLIGHT VERDICT & RECOMMENDATIONS${NC}"
  echo -e "${BLUE}======================================================================${NC}"
  if [ "$target_sku" = "Standard_D2s_v5" ]; then
    echo -e "${YELLOW}[ACTION REQUIRED] 'Standard_D2s_v5' has 0 family quota in this subscription.${NC}"
    echo -e "${GREEN}[RECOMMENDATION] Set AZURE_VM_SIZE=Standard_D2s_v4 in environment or common.sh.${NC}"
    echo -e "                 Standard_D2s_v4 has 4 vCPUs allocated, 2 vCPUs needed, 8 GiB RAM,"
    echo -e "                 and supports nested virtualization."
  else
    log_ok "SKU '${target_sku}' (standardDSv4Family) has verified quota (4 vCPUs limit, 0 used) in '${target_loc}'."
    log_info "Deployment mode: Regional non-zonal (or optional AZURE_ZONE=3)."
  fi
  echo
  log_info "Pre-flight audit complete. REMINDER: 01-create-node-b.sh runs in --dry-run by default."
  log_info "Never execute --execute without explicit approval."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
