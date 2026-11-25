import React, { useState, useMemo } from "react";
import {
  GitFork,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Filter,
  Search,
  Info,
  X,
  Cpu,
  Layers,
} from "lucide-react";
import { Decision } from "../api";

interface DecisionsViewProps {
  decisions: Decision[];
}

export const DecisionsView: React.FC<DecisionsViewProps> = ({ decisions }) => {
  const [filterNode, setFilterNode] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(null);

  const filtered = useMemo(() => {
    return decisions.filter((d) => {
      const matchSearch =
        (d.vm_id && d.vm_id.toLowerCase().includes(search.toLowerCase())) ||
        d.reason.toLowerCase().includes(search.toLowerCase());
      const matchNode =
        filterNode === "all" ||
        d.selected === filterNode ||
        (filterNode === "refused" && !d.selected);
      return matchSearch && matchNode;
    });
  }, [decisions, search, filterNode]);

  return (
    <div className="vc-page-container animate-fade-in">
      {/* Header */}
      <div className="vc-section-header">
        <div>
          <h2 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            Placement Decisions
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--text-muted)", marginTop: "4px" }}>
            Audit trail of node selections, memory checks, and scheduling verdicts
          </p>
        </div>
      </div>

      {/* Algorithmic Invariant Note */}
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
          <strong style={{ color: "var(--text-primary)" }}>Scheduling Invariant:</strong>
          {" "}The controller strictly enforces: <code>Reserved memory + requested memory &le; allocatable memory</code>.
          Unhealthy hosts are skipped; eligible nodes with highest available memory win; ties break deterministically by <code>node_id</code>.
          If worker TAP interfaces or slots are depleted, <code>HTTP 409</code> refusals are logged with exact node details.
        </div>
      </div>

      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          alignItems: "center",
          justifyContent: "space-between",
          backgroundColor: "var(--bg-surface)",
          padding: "14px 18px",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-sm)",
          marginBottom: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, maxWidth: "480px" }}>
          <div style={{ position: "relative", width: "100%" }}>
            <Search size={15} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by VM ID or reason..."
              style={{
                width: "100%",
                padding: "8px 10px 8px 32px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
                fontSize: "13px",
              }}
            />
          </div>

          <select
            value={filterNode}
            onChange={(e) => setFilterNode(e.target.value)}
            style={{
              padding: "8px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
              color: "var(--text-primary)",
              fontSize: "13px",
            }}
          >
            <option value="all">All Verdicts</option>
            <option value="node-a">Selected: node-a</option>
            <option value="node-b">Selected: node-b</option>
            <option value="refused">Refused / No Capacity</option>
          </select>
        </div>

        <div style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
          Showing <strong>{filtered.length}</strong> decisions
        </div>
      </div>

      {/* Decisions Table */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-sm)",
          overflow: "hidden",
        }}
      >
        <div style={{ overflowX: "auto" }}>
          <table className="vc-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Target VM</th>
                <th>Requested RAM</th>
                <th>Selected Node</th>
                <th>Reason</th>
                <th>Evaluated Candidates</th>
                <th style={{ textAlign: "right" }}>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr key={d.id}>
                  <td style={{ fontSize: "12px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                    {new Date(d.at * 1000).toLocaleString()}
                  </td>
                  <td>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "12.5px", fontWeight: 600 }}>
                      {d.vm_id || "(pre-allocation)"}
                    </span>
                  </td>
                  <td>
                    <strong>{d.requested_mb} MiB</strong>
                  </td>
                  <td>
                    {d.selected ? (
                      <span
                        style={{
                          fontSize: "11.5px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "99px",
                          backgroundColor: "var(--primary-subtle)",
                          color: "var(--primary)",
                        }}
                      >
                        {d.selected}
                      </span>
                    ) : (
                      <span
                        style={{
                          fontSize: "11.5px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "99px",
                          backgroundColor: "var(--danger-subtle)",
                          color: "var(--danger)",
                        }}
                      >
                        Refused
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{d.reason}</td>
                  <td>
                    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                      {d.candidates.map((c) => (
                        <span
                          key={c.node_id}
                          title={`${c.node_id}: ${c.available_mb} MB available · ${c.verdict}`}
                          style={{
                            fontSize: "11px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor: c.verdict === "eligible" ? "var(--primary-subtle)" : "rgba(185, 177, 165, 0.15)",
                            color: c.verdict === "eligible" ? "var(--primary)" : "var(--text-muted)",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {c.node_id}: {c.verdict}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      onClick={() => setSelectedDecision(d)}
                      style={{
                        padding: "4px 8px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border)",
                        backgroundColor: "var(--bg-card)",
                        color: "var(--text-primary)",
                        fontSize: "11.5px",
                        fontWeight: 600,
                      }}
                    >
                      Details
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "36px", color: "var(--text-muted)" }}>
                    No decisions recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Decision Detail Modal */}
      {selectedDecision && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(32, 37, 34, 0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
          onClick={() => setSelectedDecision(null)}
        >
          <div
            className="animate-fade-in"
            style={{
              width: "100%",
              maxWidth: "600px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-xl)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-modal)",
              padding: "24px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "38px",
                    height: "38px",
                    borderRadius: "10px",
                    backgroundColor: "var(--primary-subtle)",
                    color: "var(--primary)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <GitFork size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>
                    Placement Decision #{selectedDecision.id}
                  </h3>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    {new Date(selectedDecision.at * 1000).toLocaleString()}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedDecision(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", padding: "4px" }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)" }}>
                <span style={{ color: "var(--text-muted)" }}>Requested Memory:</span>
                <strong>{selectedDecision.requested_mb} MiB</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)" }}>
                <span style={{ color: "var(--text-muted)" }}>Selected Target Node:</span>
                <strong style={{ color: selectedDecision.selected ? "var(--primary)" : "var(--danger)" }}>
                  {selectedDecision.selected || "None (Refused)"}
                </strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)" }}>
                <span style={{ color: "var(--text-muted)" }}>Scheduler Reason:</span>
                <span>{selectedDecision.reason}</span>
              </div>
            </div>

            <h4 style={{ fontSize: "12.5px", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-muted)", fontWeight: 700, marginBottom: "8px" }}>
              Candidate Evaluations
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "20px" }}>
              {selectedDecision.candidates.map((c) => (
                <div
                  key={c.node_id}
                  style={{
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border)",
                    backgroundColor: "var(--bg-card)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: "13px",
                  }}
                >
                  <div>
                    <strong>{c.node_id}</strong>
                    <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                      Schedulable available: {c.available_mb} MiB
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      padding: "2px 8px",
                      borderRadius: "99px",
                      backgroundColor: c.verdict === "eligible" ? "var(--primary-subtle)" : "rgba(185, 177, 165, 0.15)",
                      color: c.verdict === "eligible" ? "var(--primary)" : "var(--text-muted)",
                    }}
                  >
                    {c.verdict}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                onClick={() => setSelectedDecision(null)}
                style={{
                  padding: "8px 18px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
