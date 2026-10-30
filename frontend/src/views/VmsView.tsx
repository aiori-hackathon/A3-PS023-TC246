import React, { useState, useMemo } from "react";
import {
  Server,
  Play,
  Square,
  Trash2,
  Terminal,
  Search,
  Filter,
  ArrowUpDown,
  Plus,
  AlertTriangle,
  Copy,
  Check,
  CheckCircle2,
  Clock,
  Layers,
  Info,
  Cpu,
  Activity,
  HardDrive,
  X,
} from "lucide-react";
import { VM, Node, api } from "../api";

interface VmsViewProps {
  vms: VM[];
  nodes: Node[];
  onRefresh: () => void;
  onOpenCreate: () => void;
  onOpenTerminal: (vm: VM) => void;
}

export const VmsView: React.FC<VmsViewProps> = ({
  vms,
  nodes,
  onRefresh,
  onOpenCreate,
  onOpenTerminal,
}) => {
  const [search, setSearch] = useState("");
  const [nodeFilter, setNodeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortField, setSortField] = useState<"name" | "status" | "memory_mb" | "node_id" | "created_at">("created_at");
  const [sortAsc, setSortAsc] = useState(false);

  // Action states
  const [actionInProgress, setActionInProgress] = useState<Record<string, string>>({}); // vmId -> actionName
  const [actionError, setActionError] = useState<{ vmId: string; error: string } | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<VM | null>(null);
  const [detailCandidate, setDetailCandidate] = useState<VM | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleStart = async (vm: VM) => {
    setActionInProgress((prev) => ({ ...prev, [vm.id]: "Starting" }));
    setActionError(null);
    try {
      await api("POST", `/vms/${vm.id}/start`);
      onRefresh();
    } catch (err: any) {
      setActionError({ vmId: vm.id, error: `Start failed: ${err.message}` });
    } finally {
      setActionInProgress((prev) => {
        const next = { ...prev };
        delete next[vm.id];
        return next;
      });
    }
  };

  const handleStop = async (vm: VM) => {
    setActionInProgress((prev) => ({ ...prev, [vm.id]: "Stopping (escalating shutdown)" }));
    setActionError(null);
    try {
      await api("POST", `/vms/${vm.id}/stop`);
      onRefresh();
    } catch (err: any) {
      setActionError({ vmId: vm.id, error: `Stop failed: ${err.message}` });
    } finally {
      setActionInProgress((prev) => {
        const next = { ...prev };
        delete next[vm.id];
        return next;
      });
    }
  };

  const handleDelete = async () => {
    if (!deleteCandidate) return;
    const vm = deleteCandidate;
    setActionInProgress((prev) => ({ ...prev, [vm.id]: "Deleting" }));
    setDeleteCandidate(null);
    setActionError(null);

    try {
      await api("DELETE", `/vms/${vm.id}`);
      onRefresh();
    } catch (err: any) {
      setActionError({ vmId: vm.id, error: `Delete failed: ${err.message}` });
    } finally {
      setActionInProgress((prev) => {
        const next = { ...prev };
        delete next[vm.id];
        return next;
      });
    }
  };

  // Filter & Sort
  const filteredVms = useMemo(() => {
    return vms
      .filter((vm) => {
        const matchSearch =
          vm.name.toLowerCase().includes(search.toLowerCase()) ||
          vm.id.toLowerCase().includes(search.toLowerCase()) ||
          (vm.ip_address && vm.ip_address.includes(search));
        const matchNode = nodeFilter === "all" || vm.node_id === nodeFilter;
        const matchStatus = statusFilter === "all" || vm.status === statusFilter;
        return matchSearch && matchNode && matchStatus;
      })
      .sort((a, b) => {
        let valA: any = a[sortField];
        let valB: any = b[sortField];
        if (typeof valA === "string") valA = valA.toLowerCase();
        if (typeof valB === "string") valB = valB.toLowerCase();
        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
      });
  }, [vms, search, nodeFilter, statusFilter, sortField, sortAsc]);

  // Aggregate KPI stats
  const kpis = useMemo(() => {
    const total = vms.length;
    const running = vms.filter((v) => v.status === "RUNNING").length;
    const stopped = vms.filter((v) => v.status === "STOPPED").length;
    const pending = vms.filter((v) => v.status === "PENDING" || v.status === "UNKNOWN").length;
    const totalVcpus = vms.reduce((acc, v) => acc + (v.status === "RUNNING" ? v.vcpus : 0), 0);
    const totalMemMb = vms.reduce((acc, v) => acc + (["RUNNING", "PENDING", "UNKNOWN"].includes(v.status) ? v.memory_mb : 0), 0);
    return { total, running, stopped, pending, totalVcpus, totalMemMb };
  }, [vms]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const formatImageLabel = (imgId?: string) => {
    if (!imgId) return "Ubuntu 24.04";
    if (imgId === "ubuntu-24-04" || imgId === "ubuntu") return "Ubuntu 24.04 LTS";
    if (imgId === "debian-12") return "Debian 12 Bookworm";
    if (imgId === "arch-linux") return "Arch Linux";
    if (imgId === "fedora-40") return "Fedora 40 Server";
    return imgId;
  };

  return (
    <div className="vc-page-container animate-fade-in">
      {/* Header */}
      <div className="vc-section-header">
        <div>
          <h2 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            Virtual Machine Management
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--text-muted)", marginTop: "4px" }}>
            Provisioning, guest lifecycle controls, console access, and resource allocations
          </p>
        </div>

        <button
          onClick={onOpenCreate}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--primary)",
            color: "#0A1428",
            border: "none",
            fontSize: "13.5px",
            fontWeight: 700,
            boxShadow: "0 2px 10px rgba(0, 217, 255, 0.35)",
            transition: "transform 0.15s ease",
          }}
        >
          <Plus size={18} />
          <span>Create VM</span>
        </button>
      </div>

      {/* Global Action Error Alert */}
      {actionError && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--danger-subtle)",
            color: "var(--danger)",
            fontSize: "13px",
            marginBottom: "20px",
            border: "1px solid var(--danger)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertTriangle size={18} />
            <span>{actionError.error}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            style={{ background: "transparent", border: "none", color: "var(--danger)", cursor: "pointer", fontWeight: 700 }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Summary KPI Cards Grid */}
      <div className="vc-stats-grid">
        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Total MicroVMs</span>
            <Layers size={16} style={{ color: "var(--primary)" }} />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            {kpis.total}
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Registered guest instances</span>
        </div>

        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Running Instances</span>
            <CheckCircle2 size={16} style={{ color: "var(--color-emerald-green)" }} />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--color-emerald-green)", fontFamily: "var(--font-heading)" }}>
            {kpis.running}
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Active VMM processes</span>
        </div>

        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Stopped Workloads</span>
            <Square size={16} style={{ color: "var(--text-muted)" }} />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-muted)", fontFamily: "var(--font-heading)" }}>
            {kpis.stopped}
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Inactive or idle instances</span>
        </div>

        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Committed RAM</span>
            <Activity size={16} style={{ color: "var(--accent-jade)" }} />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--accent-jade)", fontFamily: "var(--font-heading)" }}>
            {(kpis.totalMemMb / 1024).toFixed(1)} GiB
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{kpis.totalVcpus} active vCPUs allocated</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="vc-toolbar">
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flex: 1, minWidth: "280px", flexWrap: "wrap" }}>
          <div style={{ position: "relative", width: "100%", maxWidth: "360px" }}>
            <Search size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, ID, or IP..."
              style={{
                width: "100%",
                padding: "9px 12px 9px 36px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
                fontSize: "13px",
              }}
            />
          </div>

          {/* Node Filter */}
          <select
            value={nodeFilter}
            onChange={(e) => setNodeFilter(e.target.value)}
            style={{
              padding: "9px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
              color: "var(--text-primary)",
              fontSize: "13px",
            }}
          >
            <option value="all">All Worker Nodes</option>
            {nodes.map((n) => (
              <option key={n.id} value={n.id}>
                {n.id} ({n.status})
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: "9px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
              color: "var(--text-primary)",
              fontSize: "13px",
            }}
          >
            <option value="all">All Statuses</option>
            <option value="RUNNING">RUNNING</option>
            <option value="STOPPED">STOPPED</option>
            <option value="PENDING">PENDING</option>
            <option value="UNKNOWN">UNKNOWN</option>
            <option value="FAILED">FAILED</option>
          </select>
        </div>

        <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Showing <strong>{filteredVms.length}</strong> of {vms.length} microVMs
        </div>
      </div>

      {/* VM Table with Standard Spacing */}
      <div className="vc-table-container">
        <div className="vc-table-scroll">
          <table className="vc-table">
            <thead>
              <tr>
                <th onClick={() => toggleSort("name")} style={{ cursor: "pointer" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>VM Name</span>
                    <ArrowUpDown size={13} />
                  </div>
                </th>
                <th>Instance ID</th>
                <th>Operating System</th>
                <th onClick={() => toggleSort("node_id")} style={{ cursor: "pointer" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>Host Node</span>
                    <ArrowUpDown size={13} />
                  </div>
                </th>
                <th onClick={() => toggleSort("status")} style={{ cursor: "pointer" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>Status</span>
                    <ArrowUpDown size={13} />
                  </div>
                </th>
                <th onClick={() => toggleSort("memory_mb")} style={{ cursor: "pointer" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>Resources</span>
                    <ArrowUpDown size={13} />
                  </div>
                </th>
                <th>Guest IP Address</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredVms.map((vm) => {
                const isRunning = vm.status === "RUNNING";
                const isStopped = vm.status === "STOPPED";
                const currentAction = actionInProgress[vm.id];

                return (
                  <tr key={vm.id}>
                    {/* VM Name */}
                    <td>
                      <div
                        style={{ fontWeight: 700, color: "var(--text-primary)", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                        onClick={() => setDetailCandidate(vm)}
                      >
                        <span style={{ fontSize: "14px" }}>{vm.name}</span>
                        <Info size={14} style={{ color: "var(--text-muted)" }} />
                      </div>
                      {currentAction && (
                        <div style={{ fontSize: "11px", color: "var(--warning)", fontWeight: 600, marginTop: "2px" }}>
                          {currentAction}...
                        </div>
                      )}
                    </td>

                    {/* Instance ID */}
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text-muted)" }}>
                          {vm.id}
                        </span>
                        <button
                          onClick={() => handleCopy(vm.id, vm.id)}
                          title="Copy VM ID"
                          style={{ background: "transparent", border: "none", color: "var(--text-muted)", padding: "2px" }}
                        >
                          {copiedId === vm.id ? <Check size={12} style={{ color: "var(--primary)" }} /> : <Copy size={12} />}
                        </button>
                      </div>
                    </td>

                    {/* Operating System / Image */}
                    <td>
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 600,
                          padding: "3px 9px",
                          borderRadius: "6px",
                          backgroundColor: "rgba(185, 177, 165, 0.12)",
                          color: "var(--text-primary)",
                          display: "inline-block",
                        }}
                      >
                        {formatImageLabel(vm.image)}
                      </span>
                    </td>

                    {/* Host Node */}
                    <td>
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 600,
                          padding: "3px 8px",
                          borderRadius: "4px",
                          backgroundColor: vm.node_id === "node-a" ? "rgba(24, 201, 167, 0.12)" : "rgba(147, 102, 241, 0.12)",
                          color: vm.node_id === "node-a" ? "var(--accent-jade)" : "var(--accent-violet)",
                        }}
                      >
                        {vm.node_id}
                      </span>
                    </td>

                    {/* Status Badge */}
                    <td>
                      <span
                        style={{
                          fontSize: "11.5px",
                          fontWeight: 700,
                          padding: "3px 10px",
                          borderRadius: "99px",
                          backgroundColor:
                            isRunning
                              ? "rgba(22, 138, 98, 0.12)"
                              : isStopped
                              ? "rgba(185, 177, 165, 0.15)"
                              : "var(--warning-subtle)",
                          color:
                            isRunning
                              ? "var(--color-emerald-green)"
                              : isStopped
                              ? "var(--text-muted)"
                              : "var(--warning)",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "5px",
                        }}
                      >
                        <span
                          style={{
                            width: "6px",
                            height: "6px",
                            borderRadius: "50%",
                            backgroundColor: isRunning ? "var(--color-emerald-green)" : isStopped ? "var(--text-muted)" : "var(--warning)",
                          }}
                        />
                        <span>{vm.status}</span>
                      </span>
                    </td>

                    {/* Resources */}
                    <td>
                      <span style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                        {vm.vcpus} vCPU · {vm.memory_mb} MB · {vm.disk_gb} GB
                      </span>
                    </td>

                    {/* Guest IP */}
                    <td>
                      {vm.ip_address ? (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "12.5px", color: "var(--text-primary)" }}>
                            {vm.ip_address}
                          </span>
                          <button
                            onClick={() => handleCopy(vm.ip_address!, `${vm.id}-ip`)}
                            title="Copy IP"
                            style={{ background: "transparent", border: "none", color: "var(--text-muted)", padding: "2px" }}
                          >
                            {copiedId === `${vm.id}-ip` ? <Check size={12} style={{ color: "var(--primary)" }} /> : <Copy size={12} />}
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>-</span>
                      )}
                    </td>

                    {/* Action Buttons with Comfort Spacing */}
                    <td style={{ textAlign: "right" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "8px" }}>
                        {/* Start Button */}
                        <button
                          onClick={() => handleStart(vm)}
                          disabled={isRunning || !!currentAction}
                          title="Start VM"
                          style={{
                            padding: "6px 10px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border)",
                            backgroundColor: "var(--bg-card)",
                            color: isRunning ? "var(--text-muted)" : "var(--primary)",
                            cursor: isRunning || !!currentAction ? "not-allowed" : "pointer",
                            opacity: isRunning ? 0.35 : 1,
                            display: "flex",
                            alignItems: "center",
                            gap: "5px",
                            fontSize: "12px",
                            fontWeight: 600,
                          }}
                        >
                          <Play size={13} />
                          <span>Start</span>
                        </button>

                        {/* Stop Button */}
                        <button
                          onClick={() => handleStop(vm)}
                          disabled={isStopped || !!currentAction}
                          title="Stop VM"
                          style={{
                            padding: "6px 10px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border)",
                            backgroundColor: "var(--bg-card)",
                            color: isStopped ? "var(--text-muted)" : "var(--warning)",
                            cursor: isStopped || !!currentAction ? "not-allowed" : "pointer",
                            opacity: isStopped ? 0.35 : 1,
                            display: "flex",
                            alignItems: "center",
                            gap: "5px",
                            fontSize: "12px",
                            fontWeight: 600,
                          }}
                        >
                          <Square size={13} />
                          <span>Stop</span>
                        </button>

                        {/* Terminal Button */}
                        <button
                          onClick={() => onOpenTerminal(vm)}
                          disabled={!isRunning || !vm.ip_address}
                          title={isRunning ? "Launch Terminal Session" : "VM must be RUNNING to open terminal"}
                          style={{
                            padding: "6px 12px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border)",
                            backgroundColor: isRunning ? "var(--primary-subtle)" : "var(--bg-card)",
                            color: isRunning ? "var(--primary)" : "var(--text-muted)",
                            fontSize: "12px",
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            gap: "5px",
                            opacity: isRunning ? 1 : 0.45,
                            cursor: isRunning ? "pointer" : "not-allowed",
                          }}
                        >
                          <Terminal size={13} />
                          <span>Terminal</span>
                        </button>

                        {/* Delete Button */}
                        <button
                          onClick={() => setDeleteCandidate(vm)}
                          disabled={!!currentAction}
                          title="Delete VM"
                          style={{
                            padding: "6px 9px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border)",
                            backgroundColor: "var(--bg-card)",
                            color: "var(--danger)",
                            fontSize: "12px",
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {filteredVms.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", padding: "48px 20px", color: "var(--text-muted)", fontSize: "13.5px" }}>
                    {search || nodeFilter !== "all" || statusFilter !== "all"
                      ? "No virtual machines match your filter criteria."
                      : "No virtual machines exist yet. Click 'Create VM' to deploy a new microVM instance."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteCandidate && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(16, 24, 39, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
          onClick={() => setDeleteCandidate(null)}
        >
          <div
            className="animate-fade-in"
            style={{
              width: "100%",
              maxWidth: "480px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-xl)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-modal)",
              padding: "28px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "18px" }}>
              <div
                style={{
                  width: "46px",
                  height: "46px",
                  borderRadius: "14px",
                  backgroundColor: "var(--danger-subtle)",
                  color: "var(--danger)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: "1px solid var(--danger)",
                }}
              >
                <Trash2 size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                  Confirm VM Deletion
                </h3>
                <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                  Permanent destruction of instance and disk volumes
                </p>
              </div>
            </div>

            <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: 1.6 }}>
              Are you sure you want to delete virtual machine <strong>{deleteCandidate.name}</strong> (<code>{deleteCandidate.id}</code>) on worker node{" "}
              <strong>{deleteCandidate.node_id}</strong>? If running, the Cloud Hypervisor process will be terminated and all disk images erased.
            </p>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
              <button
                onClick={() => setDeleteCandidate(null)}
                style={{
                  padding: "9px 18px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                style={{
                  padding: "9px 20px",
                  borderRadius: "var(--radius-md)",
                  border: "none",
                  backgroundColor: "var(--danger)",
                  color: "#FFFFFF",
                  fontSize: "13px",
                  fontWeight: 700,
                  boxShadow: "0 2px 8px rgba(230, 83, 60, 0.4)",
                }}
              >
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VM Details Inspection Modal */}
      {detailCandidate && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(16, 24, 39, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
          onClick={() => setDetailCandidate(null)}
        >
          <div
            className="animate-fade-in"
            style={{
              width: "100%",
              maxWidth: "580px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-xl)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-modal)",
              padding: "28px",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: "19px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                  {detailCandidate.name}
                </h3>
                <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                  {detailCandidate.id} · Node: {detailCandidate.node_id}
                </span>
              </div>
              <button
                onClick={() => setDetailCandidate(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "4px" }}
              >
                <X size={20} />
              </button>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "14px",
                backgroundColor: "var(--bg-card)",
                padding: "18px",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border)",
                fontSize: "13px",
              }}
            >
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Lifecycle Status</span>
                <strong style={{ color: detailCandidate.status === "RUNNING" ? "var(--color-emerald-green)" : "var(--text-muted)", fontSize: "14px" }}>
                  {detailCandidate.status}
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Operating System</span>
                <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>
                  {formatImageLabel(detailCandidate.image)}
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Guest IP Address</span>
                <strong style={{ color: "var(--primary)", fontFamily: "var(--font-mono)", fontSize: "14px" }}>
                  {detailCandidate.ip_address || "None"}
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>vCPU / RAM Allocation</span>
                <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>
                  {detailCandidate.vcpus} vCPU · {detailCandidate.memory_mb} MB
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Root Disk Capacity</span>
                <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>
                  {detailCandidate.disk_gb} GiB RAW
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Created At</span>
                <span style={{ color: "var(--text-secondary)", fontSize: "12px", fontFamily: "var(--font-mono)" }}>
                  {new Date(detailCandidate.created_at * 1000).toLocaleString()}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              {detailCandidate.status === "RUNNING" && detailCandidate.ip_address && (
                <button
                  onClick={() => {
                    const vm = detailCandidate;
                    setDetailCandidate(null);
                    onOpenTerminal(vm);
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "9px 18px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--primary)",
                    color: "#0A1428",
                    border: "none",
                    fontSize: "13px",
                    fontWeight: 700,
                  }}
                >
                  <Terminal size={14} />
                  <span>Launch Terminal</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
