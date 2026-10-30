import React, { useState } from "react";
import {
  Cpu,
  Server,
  Activity,
  HardDrive,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  X,
  Layers,
  Terminal,
  ShieldCheck,
  Zap,
  LineChart as ChartIcon,
  ArrowDownRight,
  ArrowUpRight,
} from "lucide-react";
import { motion } from "framer-motion";
import { Node, VM, EventItem } from "../api";
import { SystemMonitor } from "../components/SystemMonitor";

interface NodesViewProps {
  nodes: Node[];
  vms: VM[];
  events: EventItem[];
  onOpenTerminal: (vm: VM) => void;
}

export const NodesView: React.FC<NodesViewProps> = ({ nodes, vms, events, onOpenTerminal }) => {
  const [activeTab, setActiveTab] = useState<"overview" | "monitor">("overview");
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [inspectorTab, setInspectorTab] = useState<"monitor" | "specs" | "vms" | "events">("monitor");
  const [monitorNodeId, setMonitorNodeId] = useState<string>(nodes[0]?.id || "node-a");

  const getHeartbeatAge = (timestamp: number | null) => {
    if (!timestamp) return { text: "Never", isStale: true };
    const diffSec = Math.max(0, Math.round(Date.now() / 1000 - timestamp));
    if (diffSec < 60) return { text: `${diffSec}s ago`, isStale: diffSec > 15 };
    const mins = Math.floor(diffSec / 60);
    return { text: `${mins}m ago`, isStale: true };
  };

  const nodeA = nodes.find((n) => n.id === "node-a") || nodes[0];
  const nodeB = nodes.find((n) => n.id === "node-b") || nodes[1];

  const healthyCount = nodes.filter((n) => n.status === "HEALTHY").length;

  return (
    <div className="vc-page-container animate-fade-in">
      {/* Page Header */}
      <div className="vc-section-header">
        <div>
          <h2 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            Node Management & System Monitor
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--text-muted)", marginTop: "4px" }}>
            Real-time hardware utilization, schedulable capacities, and telemetry across cluster hosts
          </p>
        </div>

        {/* View Mode Switcher */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              display: "flex",
              backgroundColor: "var(--bg-surface)",
              padding: "4px",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--border)",
            }}
          >
            <button
              onClick={() => setActiveTab("overview")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "7px 14px",
                borderRadius: "var(--radius-md)",
                border: "none",
                fontSize: "12.5px",
                fontWeight: 600,
                backgroundColor: activeTab === "overview" ? "var(--primary-subtle)" : "transparent",
                color: activeTab === "overview" ? "var(--primary)" : "var(--text-secondary)",
              }}
            >
              <Server size={15} />
              <span>Nodes Overview</span>
            </button>
            <button
              onClick={() => setActiveTab("monitor")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "7px 14px",
                borderRadius: "var(--radius-md)",
                border: "none",
                fontSize: "12.5px",
                fontWeight: 600,
                backgroundColor: activeTab === "monitor" ? "var(--primary-subtle)" : "transparent",
                color: activeTab === "monitor" ? "var(--primary)" : "var(--text-secondary)",
              }}
            >
              <ChartIcon size={15} />
              <span>System Monitor</span>
            </button>
          </div>

          <div
            style={{
              fontSize: "12px",
              color: healthyCount === nodes.length ? "var(--color-emerald-green)" : "var(--warning)",
              backgroundColor: healthyCount === nodes.length ? "rgba(22, 138, 98, 0.12)" : "var(--warning-subtle)",
              padding: "7px 14px",
              borderRadius: "var(--radius-md)",
              border: `1px solid ${healthyCount === nodes.length ? "rgba(22, 138, 98, 0.3)" : "var(--warning)"}`,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: healthyCount === nodes.length ? "var(--color-emerald-green)" : "var(--warning)",
              }}
            />
            <span>{healthyCount} / {nodes.length} Nodes Online</span>
          </div>
        </div>
      </div>

      {activeTab === "monitor" ? (
        /* DEDICATED SYSTEM MONITOR VIEW */
        <SystemMonitor
          nodes={nodes}
          selectedNodeId={monitorNodeId}
          onSelectNode={(id) => setMonitorNodeId(id)}
          showNodeSelector={true}
        />
      ) : (
        /* NODES OVERVIEW VIEW */
        <>
          {/* Nodes Cards Grid with Spacious 24px Padding */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))", gap: "24px", marginBottom: "32px" }}>
            {nodes.map((node) => {
              const total = node.memory_total_mb || 1;
              const sched = node.memory_schedulable_mb || 0;
              const nodeVms = vms.filter((v) => v.node_id === node.id);
              const activeVms = nodeVms.filter((v) => ["RUNNING", "PENDING", "UNKNOWN"].includes(v.status));
              const reserved = activeVms.reduce((acc, v) => acc + v.memory_mb, 0);
              const available = Math.max(0, sched - reserved);
              const usagePct = Math.min(100, Math.round((reserved / (sched || 1)) * 100));

              const hb = getHeartbeatAge(node.last_heartbeat);
              const isHealthy = node.status === "HEALTHY" && !hb.isStale;
              const isDegraded = node.status === "HEALTHY" && hb.isStale;

              const isNodeB = node.id === "node-b";

              return (
                <motion.div
                  key={node.id}
                  whileHover={{ y: -3 }}
                  style={{
                    backgroundColor: "var(--bg-surface)",
                    borderRadius: "var(--radius-xl)",
                    border: "1px solid var(--border)",
                    padding: "26px",
                    boxShadow: "var(--shadow-sm)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "20px",
                    cursor: "pointer",
                    transition: "border-color 0.2s ease",
                  }}
                  onClick={() => {
                    setSelectedNode(node);
                    setInspectorTab("monitor");
                  }}
                >
                  {/* Card Header */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                      <div
                        style={{
                          width: "46px",
                          height: "46px",
                          borderRadius: "14px",
                          backgroundColor: isHealthy ? "var(--primary-subtle)" : isDegraded ? "var(--warning-subtle)" : "var(--danger-subtle)",
                          color: isHealthy ? "var(--primary)" : isDegraded ? "var(--warning)" : "var(--danger)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          border: "1px solid var(--border)",
                        }}
                      >
                        <Server size={24} />
                      </div>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                            {node.id}
                          </h3>
                          <span
                            style={{
                              fontSize: "11px",
                              fontFamily: "var(--font-mono)",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              backgroundColor: "var(--bg-card)",
                              border: "1px solid var(--border)",
                              color: "var(--text-muted)",
                            }}
                          >
                            {isNodeB ? "Nested KVM Node" : "Host Fedora Node"}
                          </span>
                        </div>
                        <div style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginTop: "3px" }}>
                          {node.url}
                        </div>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "5px 12px",
                        borderRadius: "99px",
                        fontSize: "12px",
                        fontWeight: 700,
                        backgroundColor: isHealthy ? "rgba(22, 138, 98, 0.12)" : isDegraded ? "var(--warning-subtle)" : "var(--danger-subtle)",
                        color: isHealthy ? "var(--color-emerald-green)" : isDegraded ? "var(--warning)" : "var(--danger)",
                        border: `1px solid ${isHealthy ? "rgba(22, 138, 98, 0.3)" : "var(--border)"}`,
                      }}
                    >
                      {isHealthy ? <CheckCircle2 size={14} /> : isDegraded ? <AlertTriangle size={14} /> : <XCircle size={14} />}
                      <span>{isHealthy ? "HEALTHY" : isDegraded ? "DEGRADED" : "CRITICAL"}</span>
                    </div>
                  </div>

                  {/* Telemetry Grid (CPU, RAM, Disk, Net) */}
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: "12px",
                      padding: "16px",
                      borderRadius: "var(--radius-lg)",
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block" }}>
                        Live CPU Usage
                      </span>
                      <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginTop: "2px" }}>
                        <strong style={{ fontSize: "16px", color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                          {node.cpu_percent !== undefined ? `${node.cpu_percent}%` : "-"}
                        </strong>
                        <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                          ({node.cpu_total || 0} cores)
                        </span>
                      </div>
                    </div>

                    <div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block" }}>
                        Memory In Use
                      </span>
                      <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginTop: "2px" }}>
                        <strong style={{ fontSize: "16px", color: "var(--accent-jade)", fontFamily: "var(--font-heading)" }}>
                          {node.memory_percent !== undefined ? `${node.memory_percent}%` : "-"}
                        </strong>
                        <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                          {node.memory_used_mb ? `${(node.memory_used_mb / 1024).toFixed(1)} GiB` : "-"}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block" }}>
                        Root Storage Used
                      </span>
                      <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginTop: "2px" }}>
                        <strong style={{ fontSize: "16px", color: "var(--accent-violet)", fontFamily: "var(--font-heading)" }}>
                          {node.disk_percent !== undefined ? `${node.disk_percent}%` : "-"}
                        </strong>
                        <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                          {node.disk_used_mb ? `${(node.disk_used_mb / 1024).toFixed(1)} GiB` : "-"}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block" }}>
                        Network Throughput
                      </span>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px", fontSize: "12px", fontFamily: "var(--font-mono)" }}>
                        <span style={{ color: "var(--primary)", display: "flex", alignItems: "center" }}>
                          <ArrowDownRight size={13} /> {node.network_rx_kbps || 0}
                        </span>
                        <span style={{ color: "var(--accent-violet)", display: "flex", alignItems: "center" }}>
                          <ArrowUpRight size={13} /> {node.network_tx_kbps || 0}
                        </span>
                        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>K/s</span>
                      </div>
                    </div>
                  </div>

                  {/* Schedulable Allocation Bar */}
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "8px" }}>
                      <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Schedulable Allocation</span>
                      <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {reserved} / {sched} MiB ({usagePct}%)
                      </span>
                    </div>
                    <div
                      style={{
                        height: "10px",
                        backgroundColor: "var(--border)",
                        borderRadius: "6px",
                        overflow: "hidden",
                        display: "flex",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${usagePct}%`,
                          backgroundColor: usagePct > 85 ? "var(--danger)" : usagePct > 65 ? "var(--warning)" : "var(--primary)",
                          borderRadius: "6px",
                          transition: "width 0.3s ease",
                        }}
                      />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", color: "var(--text-muted)", marginTop: "6px" }}>
                      <span>Host Reserve: 1024 MiB</span>
                      <span>Physical RAM: {(total / 1024).toFixed(1)} GiB</span>
                    </div>
                  </div>

                  {/* Card Footer */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      paddingTop: "14px",
                      borderTop: "1px solid var(--border-subtle)",
                      fontSize: "12.5px",
                      color: "var(--primary)",
                      fontWeight: 600,
                    }}
                  >
                    <span>Inspect Live System Monitor & Telemetry</span>
                    <ExternalLink size={15} />
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Cluster Architecture Comparison Table */}
          <div className="vc-table-container">
            <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Cluster Node Architecture & Telemetry Specs
                </h3>
                <p style={{ fontSize: "12.5px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Hardware capabilities, isolation boundaries, and direct-kernel execution profiles
                </p>
              </div>
            </div>

            <div className="vc-table-scroll">
              <table className="vc-table">
                <thead>
                  <tr>
                    <th>Capability / Dimension</th>
                    <th>Node A (Host Fedora)</th>
                    <th>Node B (Nested KVM)</th>
                    <th>Operational Notes</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ fontWeight: 600 }}>Host Virtualization</td>
                    <td>ASUS TUF A15 (AMD Ryzen 7 7445HS)</td>
                    <td>Ubuntu 24.04 nested microVM on /dev/kvm</td>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>Dual KVM-accelerated hypervisor hosts</td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>Logical CPU Cores</td>
                    <td>{nodeA?.cpu_total || 12} vCPUs</td>
                    <td>{nodeB?.cpu_total || 4} vCPUs</td>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>Host hardware threads vs allocated outer VM vCPUs</td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>Physical / Total RAM</td>
                    <td>{nodeA?.memory_total_mb || 15237} MiB</td>
                    <td>{nodeB?.memory_total_mb || 3931} MiB</td>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>Enforces 1024 MiB host safety reserve invariant</td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>Worker Transport</td>
                    <td>127.0.0.1:8001</td>
                    <td>192.168.100.17:8002</td>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>Authenticated HTTP + Per-worker bearer tokens</td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>Guest IP Range</td>
                    <td>192.168.100.10 - 13 (br-ps023)</td>
                    <td>10.77.0.10 - 13 (br-inner via route)</td>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>Independent CIDR pools with host kernel routing</td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>Resident Workloads</td>
                    <td>{vms.filter((v) => v.node_id === (nodeA?.id || "node-a")).length} instances</td>
                    <td>{vms.filter((v) => v.node_id === (nodeB?.id || "node-b")).length} instances</td>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>Dynamic memory-based placement scheduler</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Node Inspector Modal */}
      {selectedNode && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(20, 25, 23, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
          onClick={() => setSelectedNode(null)}
        >
          <div
            className="animate-fade-in"
            style={{
              width: "100%",
              maxWidth: "860px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-xl)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-modal)",
              padding: "28px",
              maxHeight: "92vh",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "12px",
                    backgroundColor: "var(--primary-subtle)",
                    color: "var(--primary)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "1px solid var(--border)",
                  }}
                >
                  <Server size={24} />
                </div>
                <div>
                  <h3 style={{ fontSize: "19px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                    Node Inspector: {selectedNode.id}
                  </h3>
                  <div style={{ fontSize: "12.5px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    {selectedNode.url}
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "6px" }}
              >
                <X size={22} />
              </button>
            </div>

            {/* Inspector Navigation Tabs */}
            <div
              style={{
                display: "flex",
                gap: "8px",
                borderBottom: "1px solid var(--border)",
                paddingBottom: "12px",
              }}
            >
              {[
                { id: "monitor", label: "Real-Time Telemetry", icon: ChartIcon },
                { id: "specs", label: "Capacity & Specs", icon: Cpu },
                { id: "vms", label: `Hosted Workloads (${vms.filter((v) => v.node_id === selectedNode.id).length})`, icon: Layers },
                { id: "events", label: "Node Events", icon: Clock },
              ].map((tab) => {
                const Icon = tab.icon;
                const isSelected = inspectorTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setInspectorTab(tab.id as any)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "7px 14px",
                      borderRadius: "var(--radius-md)",
                      border: "none",
                      fontSize: "12.5px",
                      fontWeight: 600,
                      backgroundColor: isSelected ? "var(--primary-subtle)" : "transparent",
                      color: isSelected ? "var(--primary)" : "var(--text-muted)",
                    }}
                  >
                    <Icon size={14} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tab 1: Real-Time Telemetry Monitor */}
            {inspectorTab === "monitor" && (
              <SystemMonitor
                nodes={[selectedNode]}
                selectedNodeId={selectedNode.id}
                showNodeSelector={false}
              />
            )}

            {/* Tab 2: Capacity & Specifications */}
            {inspectorTab === "specs" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
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
                    <span style={{ color: "var(--text-muted)", display: "block" }}>Physical Memory</span>
                    <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)", fontSize: "15px" }}>
                      {selectedNode.memory_total_mb} MiB
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)", display: "block" }}>Host Reserve</span>
                    <strong style={{ color: "var(--text-secondary)", fontSize: "15px" }}>1024 MiB (enforced)</strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)", display: "block" }}>Schedulable Capacity</span>
                    <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)", fontSize: "15px" }}>
                      {selectedNode.memory_schedulable_mb} MiB
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)", display: "block" }}>Allocated Memory</span>
                    <strong style={{ color: "var(--primary)", fontFamily: "var(--font-mono)", fontSize: "15px" }}>
                      {vms
                        .filter((v) => v.node_id === selectedNode.id && ["RUNNING", "PENDING", "UNKNOWN"].includes(v.status))
                        .reduce((acc, v) => acc + v.memory_mb, 0)} MiB
                    </strong>
                  </div>
                </div>

                <div
                  style={{
                    padding: "16px",
                    borderRadius: "var(--radius-lg)",
                    backgroundColor: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    fontSize: "12.5px",
                    color: "var(--text-secondary)",
                    lineHeight: 1.6,
                  }}
                >
                  <strong style={{ color: "var(--text-primary)", display: "block", marginBottom: "4px" }}>
                    Memory Invariant Rule:
                  </strong>
                  The controller scheduler never starves worker hosts by reserving 1024 MiB for host operating system processes.
                  VM creation requests exceeding <code>memory_schedulable_mb - allocated_mb</code> are refused with HTTP 409 and logged to placement decisions.
                </div>
              </div>
            )}

            {/* Tab 3: Resident MicroVMs */}
            {inspectorTab === "vms" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {vms.filter((v) => v.node_id === selectedNode.id).length === 0 ? (
                  <div style={{ textAlign: "center", padding: "36px", color: "var(--text-muted)", fontSize: "13px" }}>
                    No microVMs are currently resident on {selectedNode.id}.
                  </div>
                ) : (
                  vms
                    .filter((v) => v.node_id === selectedNode.id)
                    .map((vm) => (
                      <div
                        key={vm.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "14px 18px",
                          borderRadius: "var(--radius-md)",
                          backgroundColor: "var(--bg-card)",
                          border: "1px solid var(--border)",
                        }}
                      >
                        <div>
                          <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>{vm.name}</strong>
                          <span style={{ fontSize: "12px", color: "var(--text-muted)", marginLeft: "8px", fontFamily: "var(--font-mono)" }}>
                            {vm.id}
                          </span>
                          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "3px" }}>
                            {vm.vcpus} vCPU · {vm.memory_mb} MB RAM · IP: {vm.ip_address || "None"} · Image: {vm.image || "ubuntu-24-04"}
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: 700,
                              padding: "3px 9px",
                              borderRadius: "99px",
                              backgroundColor: vm.status === "RUNNING" ? "var(--primary-subtle)" : "rgba(182, 183, 172, 0.15)",
                              color: vm.status === "RUNNING" ? "var(--primary)" : "var(--text-muted)",
                            }}
                          >
                            {vm.status}
                          </span>

                          {vm.status === "RUNNING" && vm.ip_address && (
                            <button
                              onClick={() => {
                                setSelectedNode(null);
                                onOpenTerminal(vm);
                              }}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "5px",
                                padding: "6px 12px",
                                borderRadius: "var(--radius-sm)",
                                border: "1px solid var(--border)",
                                backgroundColor: "var(--bg-surface)",
                                color: "var(--text-primary)",
                                fontSize: "12px",
                                fontWeight: 600,
                              }}
                            >
                              <Terminal size={13} />
                              <span>Terminal</span>
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                )}
              </div>
            )}

            {/* Tab 4: Node Events */}
            {inspectorTab === "events" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {events
                  .filter((e) => e.message.includes(selectedNode.id) || (e.details && e.details.includes(selectedNode.id)))
                  .slice(0, 15)
                  .map((ev) => (
                    <div
                      key={ev.id}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "var(--radius-md)",
                        backgroundColor: "var(--bg-card)",
                        border: "1px solid var(--border)",
                        fontSize: "12.5px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor: ev.level === "ERROR" ? "var(--danger-subtle)" : ev.level === "WARNING" ? "var(--warning-subtle)" : "var(--primary-subtle)",
                            color: ev.level === "ERROR" ? "var(--danger)" : ev.level === "WARNING" ? "var(--warning)" : "var(--primary)",
                          }}
                        >
                          {ev.event_type}
                        </span>
                        <span style={{ color: "var(--text-primary)" }}>{ev.message}</span>
                      </div>
                      <span style={{ color: "var(--text-muted)", fontSize: "11px", fontFamily: "var(--font-mono)" }}>
                        {new Date(ev.at * 1000).toTimeString().split(" ")[0]}
                      </span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
