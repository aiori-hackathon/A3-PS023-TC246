export interface Node {
  id: string;
  url: string;
  status: "HEALTHY" | "UNHEALTHY" | "UNKNOWN" | string;
  memory_total_mb: number;
  memory_schedulable_mb: number;
  memory_available_mb?: number;
  memory_used_mb?: number;
  memory_percent?: number;
  cpu_total: number;
  cpu_percent?: number;
  disk_total_mb?: number;
  disk_used_mb?: number;
  disk_percent?: number;
  network_rx_kbps?: number;
  network_tx_kbps?: number;
  vms_running: number;
  last_heartbeat: number | null;
  cgroups_enabled?: boolean;
}

export interface NodeMetricSample {
  id: number;
  node_id: string;
  timestamp: number;
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_available_mb: number;
  memory_percent: number;
  disk_used_mb: number;
  disk_total_mb: number;
  disk_percent: number;
  network_rx_kbps: number;
  network_tx_kbps: number;
  vms_running: number;
}

export interface ClusterMetrics {
  total_nodes: number;
  healthy_nodes: number;
  total_cpu_cores: number;
  cluster_cpu_percent: number;
  total_memory_mb: number;
  used_memory_mb: number;
  available_memory_mb: number;
  schedulable_memory_mb: number;
  cluster_memory_percent: number;
  timestamp: number;
}

export interface NodeResources {
  node_id: string;
  cpu_total: number;
  cpu_percent: number;
  cpu_committed_vcpus: number;
  memory_total_mb: number;
  memory_available_mb: number;
  memory_committed_mb: number;
  memory_schedulable_mb: number;
  vms_total: number;
  vms_running: number;
}

export interface VM {
  id: string;
  name: string;
  node_id: string;
  worker_vm_id?: string;
  status: "RUNNING" | "STOPPED" | "PENDING" | "UNKNOWN" | "FAILED" | "EVACUATING" | "EVACUATION_FAILED" | string;
  vcpus: number;
  memory_mb: number;
  disk_gb: number;
  ip_address?: string | null;
  created_at: number;
  image?: string;
  ha?: boolean;
  evacuation_error?: string | null;
  recovery_time_s?: number | null;
  cgroups?: boolean;
  cgroup_limits?: {
    memory_max_bytes?: number;
    memory_overhead_mb?: number;
    cpu_quota?: number;
    cpu_period?: number;
    cpu_headroom?: number;
    pids_max?: number;
  } | null;
}

export interface Candidate {
  node_id: string;
  healthy: boolean;
  available_mb: number;
  verdict: string;
}

export interface Decision {
  id: number;
  vm_id: string | null;
  at: number;
  requested_mb: number;
  selected: string | null;
  reason: string;
  candidates: Candidate[];
}

export interface EventItem {
  id: number;
  at: number;
  event_type: string;
  level: "INFO" | "WARNING" | "ERROR";
  message: string;
  details?: string | null;
  source?: string;
}

export interface OSImage {
  id: string;
  name: string;
  distro: string;
  version: string;
  arch: string;
  format: string;
  path?: string | null;
  disk_size_bytes?: number | null;
  status: "AVAILABLE" | "NOT_DOWNLOADED" | "MISSING" | "VALIDATING" | "FAILED" | "INCOMPATIBLE_KERNEL" | string;
  verification_status: "VERIFIED" | "OFFICIAL" | "COMMUNITY" | "FAILED" | "VERIFIED_INCOMPATIBLE" | string;
  checksum?: string | null;
  download_url?: string | null;
  kernel_compat?: "COMPATIBLE" | "INCOMPATIBLE_BTRFS" | "REQUIRES_CONVERSION" | string;
  notes?: string | null;
  created_at: number;
}

export interface CandidatePreview {
  node_id: string;
  healthy: boolean;
  memory_total_mb: number;
  memory_schedulable_mb: number;
  memory_reserved_mb: number;
  memory_available_mb: number;
  estimated_remaining_mb: number;
  can_accommodate: boolean;
  vms_running: number;
}

export interface SchedulerPreviewResult {
  requested_mb: number;
  requested_vcpus: number;
  recommended_node: string | null;
  reason: string;
  can_accommodate: boolean;
  nodes: CandidatePreview[];
}

// Token storage in memory with sessionStorage & localStorage persistence
let currentToken = "";
try {
  currentToken = sessionStorage.getItem("vmc_token") || localStorage.getItem("vmc_token") || sessionStorage.getItem("ps023token") || "";
} catch {
  // Ignore storage restriction
}

export function getToken(): string {
  return currentToken;
}

export function setToken(token: string): void {
  currentToken = token.trim();
  try {
    sessionStorage.setItem("vmc_token", currentToken);
    localStorage.setItem("vmc_token", currentToken);
    sessionStorage.setItem("ps023token", currentToken);
  } catch {
    // Ignore
  }
}

export function clearToken(): void {
  currentToken = "";
  try {
    sessionStorage.removeItem("vmc_token");
    localStorage.removeItem("vmc_token");
    sessionStorage.removeItem("ps023token");
  } catch {
    // Ignore
  }
}

export async function initAuth(): Promise<string> {
  if (currentToken) return currentToken;
  try {
    const res = await fetch("/api/auth/token");
    if (res.ok) {
      const data = await res.json();
      if (data && data.token) {
        setToken(data.token);
        return data.token;
      }
    }
  } catch {
    // Ignore in production
  }
  return currentToken;
}

export async function api<T>(method: string, path: string, body?: any): Promise<T> {
  if (!currentToken) {
    await initAuth();
  }

  const headers: Record<string, string> = {};
  if (currentToken) {
    headers["Authorization"] = `Bearer ${currentToken}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) {
    return null as T;
  }

  let data: any = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("vmc:auth-unauthorized"));
    }
  }

  if (!res.ok) {
    const detail = data && data.detail;
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail || data);
    throw new Error(msg || `HTTP ${res.status}`);
  }

  return data as T;
}
