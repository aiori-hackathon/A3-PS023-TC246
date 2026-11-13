import React, { useMemo } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Activity,
  GitFork,
  Server,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Info,
} from "lucide-react";
import { Decision, EventItem, VM, Node } from "../api";

interface FailoverViewProps {
  decisions: Decision[];
  events: EventItem[];
  vms: VM[];
  nodes: Node[];
  onOpenTerminal?: (vm: VM) => void;
}

export const FailoverView: React.FC<FailoverViewProps> = ({
  decisions,
  events,
  vms,
  nodes,
  onOpenTerminal,
}) => {
  // Extract strictly REAL failover events & decisions
  const failoverEvents = useMemo(() => {
    return events.filter((e) => {
      const msg = (e.message || "").toLowerCase();
      const type = (e.event_type || "").toLowerCase();
      return (
        type.includes("evacuat") ||
        type.includes("failover") ||
        type.includes("reconcile") ||
        msg.includes("evacuat") ||
        msg.includes("unhealthy") ||
        msg.includes("failover") ||
        msg.includes("tombstone") ||
        msg.includes("fenc")
      );
    });
  }, [events]);

  const failoverDecisions = useMemo(() => {
    return decisions.filter((d) => {
      const r = (d.reason || "").toLowerCase();
      return r.includes("evacuat") || r.includes("unhealthy") || r.includes("failover");
    });
  }, [decisions]);

  const evacuatedVms = useMemo(() => {
    return vms.filter(
      (v) =>
        v.recovery_time_s != null ||
        v.status === "EVACUATING" ||
        v.status === "EVACUATION_FAILED" ||
        Boolean(v.evacuation_error)
    );
  }, [vms]);

  const hasFailoverData =
    failoverEvents.length > 0 || failoverDecisions.length > 0 || evacuatedVms.length > 0;

  // Extract real recovery time from VMs or decisions
  const latestRecoveryTime = useMemo(() => {
    let latest: number | null = null;
    for (const v of vms) {
      if (v.recovery_time_s != null) {
        if (latest === null || v.recovery_time_s > latest) {
          latest = v.recovery_time_s;
        }
      }
    }
    return latest;
  }, [vms]);

  const totalEvacuations = evacuatedVms.length || failoverDecisions.length;

  return (
    <div className="vc-page-container animate-fade-in">
      {/* Header */}
      <div className="vc-section-header">
        <div>
          <h2
            style={{
              fontSize: "24px",
              fontWeight: 700,
              color: "var(--text-primary)",
              fontFamily: "var(--font-heading)",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <ShieldAlert size={24} style={{ color: "var(--primary)" }} />
            <span>High Availability & Automated Failover</span>
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--text-muted)", marginTop: "4px" }}>
            Real-time audit log of failure detection, atomic auto-evacuation, and ghost-copy fencing
          </p>
        </div>
      </div>

      {/* HA Architecture Banner */}
      <div
        style={{
          display: "flex",
          gap: "14px",
          padding: "16px 20px",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-sm)",
          marginBottom: "24px",
        }}
      >
        <Info size={20} style={{ color: "var(--primary)", flexShrink: 0, marginTop: "2px" }} />
        <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
          <strong style={{ color: "var(--text-primary)" }}>Zero-Operator Self-Healing Policy:</strong>
          {" "}When a worker misses heartbeats for 15s, the controller transitions the host to <code>UNHEALTHY</code>.
          All <code>ha=true</code> VMs on the failed node are atomically placed on the healthy node, preserving memory invariants.
          Upon host restoration, stale processes are automatically fenced and terminated to eliminate split-brain dual execution.
        </div>
      </div>

      {/* KPI Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        {/* Card 1: Last Recovery Time */}
        <div
          style={{
            padding: "18px 20px",
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Last Failover Recovery Time
          </div>
          <div
            style={{
              fontSize: "24px",
              fontWeight: 800,
              fontFamily: "var(--font-mono)",
              color: latestRecoveryTime ? "var(--primary)" : "var(--text-muted)",
              marginTop: "8px",
            }}
          >
            {latestRecoveryTime ? `${latestRecoveryTime.toFixed(2)}s` : "not available"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Detection to guest RUNNING
          </div>
        </div>

        {/* Card 2: Evacuations Recorded */}
        <div
          style={{
            padding: "18px 20px",
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Total Evacuations
          </div>
          <div
            style={{
              fontSize: "24px",
              fontWeight: 800,
              fontFamily: "var(--font-mono)",
              color: "var(--text-primary)",
              marginTop: "8px",
            }}
          >
            {totalEvacuations}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Automated cluster rescues
          </div>
        </div>

        {/* Card 3: Cluster HA State */}
        <div
          style={{
            padding: "18px 20px",
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
            HA Protection State
          </div>
          <div
            style={{
              fontSize: "16px",
              fontWeight: 700,
              color: nodes.every((n) => n.status === "HEALTHY") ? "var(--primary)" : "var(--danger)",
              marginTop: "12px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            {nodes.every((n) => n.status === "HEALTHY") ? (
              <>
                <ShieldCheck size={18} />
                <span>ACTIVE & HEALTHY</span>
              </>
            ) : (
              <>
                <AlertTriangle size={18} />
                <span>FAILOVER ENGAGED</span>
              </>
            )}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            {nodes.filter((n) => n.status === "HEALTHY").length}/{nodes.length} nodes operational
          </div>
        </div>
      </div>

      {/* Main Panel */}
      {!hasFailoverData ? (
        <div
          style={{
            padding: "48px 24px",
            textAlign: "center",
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <ShieldCheck size={44} style={{ color: "var(--text-muted)", margin: "0 auto 16px" }} />
          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
            no failover events yet
          </h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", maxWidth: "480px", margin: "0 auto" }}>
            No HA auto-evacuations or node failures have occurred in this session.
            When chaos testing is executed (e.g. <code>./scripts/chaos_kill_node_b.sh worker</code>),
            the controller auto-evacuation decisions and recovery timeline will appear here in real time.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Section A: Evacuated VMs */}
          {evacuatedVms.length > 0 && (
            <div
              style={{
                backgroundColor: "var(--bg-surface)",
                padding: "20px 24px",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "14px" }}>
                Evacuated Workloads
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {evacuatedVms.map((vm) => (
                  <div
                    key={vm.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "12px 16px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "14px" }}>
                          {vm.name}
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 7px",
                            borderRadius: "4px",
                            backgroundColor: "var(--primary-subtle)",
                            color: "var(--primary)",
                          }}
                        >
                          HA PROTECTED
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 7px",
                            borderRadius: "4px",
                            backgroundColor:
                              vm.status === "RUNNING"
                                ? "var(--primary-subtle)"
                                : vm.status === "EVACUATING"
                                ? "var(--warning-subtle)"
                                : "var(--danger-subtle)",
                            color:
                              vm.status === "RUNNING"
                                ? "var(--primary)"
                                : vm.status === "EVACUATING"
                                ? "var(--warning)"
                                : "var(--danger)",
                          }}
                        >
                          {vm.status}
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
                        Host Node: <strong style={{ color: "var(--text-primary)" }}>{vm.node_id}</strong>
                        {vm.ip_address && <> &bull; IP: <code style={{ color: "var(--text-primary)" }}>{vm.ip_address}</code></>}
                      </div>
                    </div>

                    <div style={{ textAlign: "right" }}>
                      {vm.recovery_time_s != null && (
                        <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--primary)", fontFamily: "var(--font-mono)" }}>
                          Recovered in {vm.recovery_time_s.toFixed(2)}s
                        </div>
                      )}
                      {vm.evacuation_error && (
                        <div style={{ fontSize: "12px", color: "var(--danger)", fontWeight: 600 }}>
                          {vm.evacuation_error}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section B: Structured Failover Decisions */}
          {failoverDecisions.length > 0 && (
            <div
              style={{
                backgroundColor: "var(--bg-surface)",
                padding: "20px 24px",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "14px" }}>
                Real Evacuation Placement Decisions
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {failoverDecisions.map((d) => (
                  <div
                    key={d.id}
                    style={{
                      padding: "12px 16px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      fontSize: "13px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                      <span style={{ fontWeight: 700, color: "var(--primary)", fontFamily: "var(--font-mono)" }}>
                        {d.vm_id || "Cluster"}
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {new Date(d.at * 1000).toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ color: "var(--text-primary)", fontWeight: 500 }}>
                      {d.reason}
                    </div>
                    {d.candidates && d.candidates.length > 0 && (
                      <div style={{ display: "flex", gap: "8px", marginTop: "8px", flexWrap: "wrap" }}>
                        {d.candidates.map((c) => (
                          <span
                            key={c.node_id}
                            style={{
                              fontSize: "11px",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              backgroundColor: c.healthy ? "var(--bg-surface)" : "var(--danger-subtle)",
                              color: c.healthy ? "var(--text-secondary)" : "var(--danger)",
                              border: "1px solid var(--border)",
                            }}
                          >
                            {c.node_id}: {c.verdict} ({c.available_mb} MB free)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section C: Audit Events */}
          {failoverEvents.length > 0 && (
            <div
              style={{
                backgroundColor: "var(--bg-surface)",
                padding: "20px 24px",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "14px" }}>
                Failover Activity Audit Trail
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {failoverEvents.slice(0, 15).map((ev) => (
                  <div
                    key={ev.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      fontSize: "12.5px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          backgroundColor:
                            ev.level === "ERROR"
                              ? "var(--danger-subtle)"
                              : ev.level === "WARNING"
                              ? "var(--warning-subtle)"
                              : "var(--primary-subtle)",
                          color:
                            ev.level === "ERROR"
                              ? "var(--danger)"
                              : ev.level === "WARNING"
                              ? "var(--warning)"
                              : "var(--primary)",
                        }}
                      >
                        {ev.event_type}
                      </span>
                      <span style={{ color: "var(--text-primary)" }}>{ev.message}</span>
                    </div>
                    <span style={{ color: "var(--text-muted)", fontSize: "11px", fontFamily: "var(--font-mono)" }}>
                      {new Date(ev.at * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
