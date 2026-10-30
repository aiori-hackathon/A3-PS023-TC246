import React, { useState } from "react";
import {
  Server,
  Cpu,
  Layers,
  HardDrive,
  Activity,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Plus,
  Play,
  Square,
  Clock,
  Terminal,
  ShieldCheck,
  RefreshCw,
  BarChart3,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import { motion } from "framer-motion";
import { Node, VM, Decision, EventItem } from "../api";
import { NavTab } from "../components/Sidebar";
import { ClusterScene } from "../components/ClusterScene";

interface OverviewViewProps {
  nodes: Node[];
  vms: VM[];
  decisions: Decision[];
  events: EventItem[];
  onOpenCreate: () => void;
  onNavigate: (tab: NavTab) => void;
  onOpenTerminal: (vm: VM) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  nodes,
  vms,
  decisions,
  events,
  onOpenCreate,
  onNavigate,
  onOpenTerminal,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedVmId, setSelectedVmId] = useState<string | null>(null);

  const runningVms = vms.filter((v) => v.status === "RUNNING");
  const stoppedVms = vms.filter((v) => v.status === "STOPPED");
  const failedVms = vms.filter((v) => v.status === "FAILED" || v.status === "UNKNOWN");
  const healthyNodes = nodes.filter((n) => n.status === "HEALTHY");

  const totalPhysicalMemMb = nodes.reduce((acc, n) => acc + (n.memory_total_mb || 0), 0);
  const totalSchedulableMb = nodes.reduce((acc, n) => acc + (n.memory_schedulable_mb || 0), 0);
  const totalReservedMb = vms.reduce(
    (acc, v) => (["RUNNING", "PENDING", "UNKNOWN"].includes(v.status) ? acc + v.memory_mb : acc),
    0
  );
  const totalAvailableMb = Math.max(0, totalSchedulableMb - totalReservedMb);

  // Resource Warnings
  const warnings: string[] = [];
  nodes.forEach((n) => {
    if (n.status !== "HEALTHY") {
      warnings.push(`Node '${n.id}' is in ${n.status} state.`);
    }
  });
  if (totalSchedulableMb > 0 && totalReservedMb / totalSchedulableMb > 0.85) {
    warnings.push("Cluster memory reservation exceeds 85% of total schedulable capacity.");
  }

  // Data for Recharts Node Memory Comparison
  const nodeMemoryData = nodes.map((n) => {
    const nodeVms = vms.filter((v) => v.node_id === n.id && ["RUNNING", "PENDING", "UNKNOWN"].includes(v.status));
    const reserved = nodeVms.reduce((acc, v) => acc + v.memory_mb, 0);
    const sched = n.memory_schedulable_mb || 0;
    const available = Math.max(0, sched - reserved);
    return {
      name: n.id,
      Reserved: reserved,
      Available: available,
      Schedulable: sched,
    };
  });

  // Data for VM Status Distribution
  const vmStatusData = [
    { name: "Running", value: runningVms.length, color: "#C1FF00" },
    { name: "Stopped", value: stoppedVms.length, color: "#9296A8" },
    { name: "Failed/Unk", value: failedVms.length, color: "#FF4C41" },
  ].filter((d) => d.value > 0);

  return (
    <div style={{ padding: "28px", maxWidth: "1440px", margin: "0 auto" }}>
      {/* Resource Warnings Banner */}
      {warnings.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "14px 18px",
            borderRadius: "var(--radius-lg)",
            backgroundColor: "rgba(230, 90, 69, 0.15)",
            border: "1px solid var(--danger)",
            color: "var(--text-primary)",
            marginBottom: "24px",
          }}
        >
          <AlertTriangle size={20} style={{ color: "var(--danger)", flexShrink: 0 }} />
          <div style={{ flex: 1, fontSize: "13.5px" }}>
            <strong>Cluster Attention Required:</strong> {warnings.join(" ")}
          </div>
        </motion.div>
      )}

      {/* Cluster Key Performance Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "28px",
        }}
      >
        {/* Total VMs */}
        <motion.div
          whileHover={{ y: -2 }}
          style={{
            backgroundColor: "var(--bg-surface)",
            padding: "20px",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>Total VMs</span>
            <Server size={18} />
          </div>
          <div style={{ fontSize: "30px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            {vms.length}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            {runningVms.length} running · {stoppedVms.length} stopped
          </div>
        </motion.div>

        {/* Running VMs */}
        <motion.div
          whileHover={{ y: -2 }}
          style={{
            backgroundColor: "var(--bg-surface)",
            padding: "20px",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--primary)", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>Running VMs</span>
            <Play size={18} />
          </div>
          <div style={{ fontSize: "30px", fontWeight: 800, color: "var(--primary)", fontFamily: "var(--font-heading)" }}>
            {runningVms.length}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>Active microVM workloads</div>
        </motion.div>

        {/* Cluster Nodes */}
        <motion.div
          whileHover={{ y: -2 }}
          style={{
            backgroundColor: "var(--bg-surface)",
            padding: "20px",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--primary)", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>Cluster Nodes</span>
            <Cpu size={18} />
          </div>
          <div style={{ fontSize: "30px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            {healthyNodes.length} <span style={{ fontSize: "18px", color: "var(--text-muted)" }}>/ {nodes.length}</span>
          </div>
          <div style={{ fontSize: "12px", color: healthyNodes.length === nodes.length ? "var(--primary)" : "var(--danger)", fontWeight: 500, marginTop: "4px" }}>
            {healthyNodes.length === nodes.length ? "All 2 Nodes Healthy" : "Degraded Availability"}
          </div>
        </motion.div>

        {/* Schedulable Memory */}
        <motion.div
          whileHover={{ y: -2 }}
          style={{
            backgroundColor: "var(--bg-surface)",
            padding: "20px",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>Schedulable RAM</span>
            <HardDrive size={18} />
          </div>
          <div style={{ fontSize: "30px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            {(totalSchedulableMb / 1024).toFixed(1)} <span style={{ fontSize: "16px", fontWeight: 500 }}>GiB</span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Physical: {(totalPhysicalMemMb / 1024).toFixed(1)} GiB
          </div>
        </motion.div>

        {/* Available Capacity */}
        <motion.div
          whileHover={{ y: -2 }}
          style={{
            backgroundColor: "var(--bg-surface)",
            padding: "20px",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--primary)", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>Available Capacity</span>
            <CheckCircle2 size={18} />
          </div>
          <div style={{ fontSize: "30px", fontWeight: 800, color: "var(--primary)", fontFamily: "var(--font-heading)" }}>
            {(totalAvailableMb / 1024).toFixed(1)} <span style={{ fontSize: "16px", fontWeight: 500 }}>GiB</span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Committed: {(totalReservedMb / 1024).toFixed(1)} GiB
          </div>
        </motion.div>
      </div>

      {/* Header & Quick Action */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            Your cluster, at a glance.
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>
            Monitor, manage, and scale your virtual machines across multiple nodes.
          </p>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <button
            onClick={() => onNavigate("explore")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "9px 16px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "rgba(16, 24, 39, 0.78)",
              color: "var(--text-primary)",
              fontSize: "13px",
              fontWeight: 600,
              border: "1px solid var(--border)",
            }}
          >
            <span>Explore 3D Universe</span>
            <ArrowRight size={14} />
          </button>
          <button
            onClick={onOpenCreate}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "9px 18px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--primary)",
              color: "#08090D",
              fontSize: "13px",
              fontWeight: 700,
              border: "none",
              boxShadow: "var(--shadow-cyan-glow)",
            }}
          >
            <Plus size={16} />
            <span>Create VM</span>
          </button>
        </div>
      </div>

      {/* Signature Feature: Interactive 3D Infrastructure Overview */}
      <div style={{ marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
              Infrastructure Topology & Live Cluster Model
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
              Interactive 3D spatial twin of the controller hub, worker nodes, and active microVM workloads
            </p>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={() => onNavigate("terminals")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "7px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--bg-surface)",
                color: "var(--text-primary)",
                fontSize: "12px",
                fontWeight: 600,
                border: "1px solid var(--border)",
              }}
            >
              <Terminal size={14} />
              <span>Open Terminals</span>
            </button>
          </div>
        </div>

        <ClusterScene
          nodes={nodes}
          vms={vms}
          selectedNodeId={selectedNodeId}
          selectedVmId={selectedVmId}
          onSelectNode={setSelectedNodeId}
          onSelectVm={setSelectedVmId}
          onOpenTerminal={onOpenTerminal}
        />
      </div>

      {/* Middle Grid: Resource Charts & Workload Operations */}
      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 0.9fr", gap: "24px", marginBottom: "28px" }}>
        {/* Node Capacity & Resource Comparison */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                Worker Memory Allocation
              </h3>
              <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                Allocated vs. Available Schedulable Memory per node (MiB)
              </p>
            </div>
            <button
              onClick={() => onNavigate("nodes")}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--primary)",
                fontSize: "13px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <span>Node Inspector</span>
              <ArrowRight size={14} />
            </button>
          </div>

          {/* Recharts Bar Chart */}
          <div style={{ height: "200px", width: "100%", marginBottom: "16px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={nodeMemoryData} layout="vertical" margin={{ top: 10, right: 20, left: 20, bottom: 0 }}>
                <XAxis type="number" stroke="#9296A8" fontSize={11} tickFormatter={(v) => `${v}M`} />
                <YAxis dataKey="name" type="category" stroke="#9296A8" fontSize={12} width={70} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#11131B",
                    borderColor: "#1F2436",
                    borderRadius: "8px",
                    color: "#F0F1FA",
                    fontSize: "12px",
                  }}
                  formatter={(value: any, name: any) => [`${value} MiB`, name]}
                />
                <Bar dataKey="Reserved" stackId="a" fill="#8832F7" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Available" stackId="a" fill="#00D9FF" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div style={{ display: "flex", justifyContent: "center", gap: "20px", fontSize: "12px", color: "var(--text-muted)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "10px", height: "10px", backgroundColor: "#8832F7", borderRadius: "2px" }} />
              <span>Allocated / Reserved</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "10px", height: "10px", backgroundColor: "#00D9FF", borderRadius: "2px" }} />
              <span>Available Capacity</span>
            </div>
          </div>
        </div>

        {/* Workload Operations & Quick Action */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                Active Instances
              </h3>
              <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>Recent microVM lifecycle states</p>
            </div>
            <button
              onClick={() => onNavigate("vms")}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--primary)",
                fontSize: "13px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <span>All VMs</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto", maxHeight: "250px" }}>
            {vms.slice(0, 5).map((vm) => (
              <div
                key={vm.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-card)",
                  border: "1px solid var(--border)",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "13.5px", color: "var(--text-primary)" }}>{vm.name}</div>
                  <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                    {vm.node_id} · {vm.vcpus} vCPU · {vm.memory_mb} MB · {vm.ip_address || "No IP"}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      padding: "2px 8px",
                      borderRadius: "99px",
                      backgroundColor: vm.status === "RUNNING" ? "var(--primary-subtle)" : "rgba(182, 183, 172, 0.15)",
                      color: vm.status === "RUNNING" ? "var(--primary)" : "var(--text-muted)",
                    }}
                  >
                    {vm.status}
                  </span>
                  {vm.status === "RUNNING" && vm.ip_address && (
                    <button
                      onClick={() => onOpenTerminal(vm)}
                      title="Open Terminal Session"
                      style={{
                        padding: "5px 9px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border)",
                        backgroundColor: "transparent",
                        color: "var(--text-primary)",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <Terminal size={12} />
                      <span>Console</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
            {vms.length === 0 && (
              <div style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)", fontSize: "13px" }}>
                No active VMs. Click "Provision VM" to create one.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Section: Latest Placement Decisions */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border)",
          padding: "24px",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
              Latest Placement Decisions
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
              Controller scheduling invariant audit and candidate evaluation breakdown
            </p>
          </div>
          <button
            onClick={() => onNavigate("decisions")}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--primary)",
              fontSize: "13px",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <span>View All Decisions</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="vc-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Target VM</th>
                <th>Requested RAM</th>
                <th>Selected Node</th>
                <th>Scheduler Reason</th>
                <th>Candidate Verdicts</th>
              </tr>
            </thead>
            <tbody>
              {decisions.slice(0, 5).map((d) => (
                <tr key={d.id}>
                  <td style={{ fontSize: "12px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                    {new Date(d.at * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "12.5px" }}>{d.vm_id || "(pre-allocation)"}</td>
                  <td style={{ fontFamily: "var(--font-mono)" }}>{d.requested_mb} MiB</td>
                  <td>
                    {d.selected ? (
                      <span style={{ fontWeight: 600, color: "var(--primary)" }}>{d.selected}</span>
                    ) : (
                      <span style={{ fontWeight: 600, color: "var(--danger)" }}>Refused</span>
                    )}
                  </td>
                  <td style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>{d.reason}</td>
                  <td>
                    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                      {d.candidates.map((c) => (
                        <span
                          key={c.node_id}
                          title={`${c.available_mb} MB available · ${c.verdict}`}
                          style={{
                            fontSize: "11px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor: c.verdict === "eligible" ? "var(--primary-subtle)" : "rgba(182, 183, 172, 0.12)",
                            color: c.verdict === "eligible" ? "var(--primary)" : "var(--text-muted)",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {c.node_id}: {c.verdict}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {decisions.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
                    No decisions recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
