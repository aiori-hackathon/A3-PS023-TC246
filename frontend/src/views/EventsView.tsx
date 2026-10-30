import React, { useState, useMemo } from "react";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Search,
  Filter,
  Info,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { EventItem } from "../api";

interface EventsViewProps {
  events: EventItem[];
}

export const EventsView: React.FC<EventsViewProps> = ({ events }) => {
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const filtered = useMemo(() => {
    return events.filter((ev) => {
      const matchSearch =
        ev.message.toLowerCase().includes(search.toLowerCase()) ||
        ev.event_type.toLowerCase().includes(search.toLowerCase()) ||
        (ev.source && ev.source.toLowerCase().includes(search.toLowerCase()));
      const matchLevel = levelFilter === "all" || ev.level === levelFilter;
      return matchSearch && matchLevel;
    });
  }, [events, search, levelFilter]);

  return (
    <div className="vc-page-container animate-fade-in">
      {/* Header */}
      <div className="vc-section-header">
        <div>
          <h2 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            Activity & Events
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--text-muted)", marginTop: "4px" }}>
            Operational audit log of VM lifecycle, worker heartbeats, scheduler decisions, and terminal sessions
          </p>
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
              placeholder="Search events, sources, or keywords..."
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
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            style={{
              padding: "8px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
              color: "var(--text-primary)",
              fontSize: "13px",
            }}
          >
            <option value="all">All Severities</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </div>

        <div style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
          Showing <strong>{filtered.length}</strong> events
        </div>
      </div>

      {/* Events Stream */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-sm)",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          {filtered.map((ev) => {
            const isExpanded = expandedId === ev.id;
            const isInfo = ev.level === "INFO";
            const isWarn = ev.level === "WARNING";
            const isError = ev.level === "ERROR";

            let detailsObj: any = null;
            if (ev.details) {
              try {
                detailsObj = JSON.parse(ev.details);
              } catch {
                detailsObj = ev.details;
              }
            }

            return (
              <div
                key={ev.id}
                style={{
                  padding: "14px 20px",
                  borderBottom: "1px solid var(--border-subtle)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  transition: "background-color 0.12s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    {/* Severity Icon */}
                    {isInfo ? (
                      <CheckCircle2 size={16} style={{ color: "var(--primary)", flexShrink: 0 }} />
                    ) : isWarn ? (
                      <AlertTriangle size={16} style={{ color: "var(--warning)", flexShrink: 0 }} />
                    ) : (
                      <XCircle size={16} style={{ color: "var(--danger)", flexShrink: 0 }} />
                    )}

                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "1px 6px",
                        borderRadius: "4px",
                        backgroundColor: isInfo ? "var(--primary-subtle)" : isWarn ? "var(--warning-subtle)" : "var(--danger-subtle)",
                        color: isInfo ? "var(--primary)" : isWarn ? "var(--warning)" : "var(--danger)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {ev.event_type}
                    </span>

                    <span style={{ fontSize: "13.5px", fontWeight: 600, color: "var(--text-primary)" }}>
                      {ev.message}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                      {new Date(ev.at * 1000).toLocaleString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", month: "short", day: "numeric" })}
                    </span>

                    {detailsObj && (
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : ev.id)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "3px",
                          background: "transparent",
                          border: "none",
                          color: "var(--primary)",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                          padding: "2px",
                        }}
                      >
                        <span>{isExpanded ? "Hide Details" : "View Details"}</span>
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded Details JSON */}
                {isExpanded && detailsObj && (
                  <div
                    style={{
                      marginTop: "8px",
                      padding: "12px",
                      backgroundColor: "var(--bg-card)",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border)",
                      fontSize: "12px",
                      fontFamily: "var(--font-mono)",
                      overflowX: "auto",
                      color: "var(--text-secondary)",
                    }}
                  >
                    <pre style={{ margin: 0 }}>
                      {typeof detailsObj === "object" ? JSON.stringify(detailsObj, null, 2) : String(detailsObj)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}

          {filtered.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)", fontSize: "13.5px" }}>
              No operational events recorded matching the current filters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
