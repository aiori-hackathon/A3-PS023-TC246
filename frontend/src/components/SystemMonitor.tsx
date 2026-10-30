import React, { useState, useEffect, useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  Cpu,
  HardDrive,
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Clock,
  Layers,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { Node, NodeMetricSample, api } from "../api";

interface SystemMonitorProps {
  nodes: Node[];
  selectedNodeId?: string;
  onSelectNode?: (nodeId: string) => void;
  showNodeSelector?: boolean;
}

type TimeRange = "5m" | "15m" | "30m" | "1h";

export const SystemMonitor: React.FC<SystemMonitorProps> = ({
  nodes,
  selectedNodeId,
  onSelectNode,
  showNodeSelector = true,
}) => {
  const activeNodeId = selectedNodeId || nodes[0]?.id || "node-a";
  const [timeRange, setTimeRange] = useState<TimeRange>("5m");
  const [metrics, setMetrics] = useState<NodeMetricSample[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // Active node metadata
  const activeNode = useMemo(
    () => nodes.find((n) => n.id === activeNodeId) || nodes[0],
    [nodes, activeNodeId]
  );

  // Fetch metrics periodically
  useEffect(() => {
    let isSubscribed = true;

    const fetchMetrics = async () => {
      if (!activeNodeId) return;
      try {
        const limitMap: Record<TimeRange, number> = {
          "5m": 60,
          "15m": 180,
          "30m": 360,
          "1h": 720,
        };
        const limit = limitMap[timeRange];
        const res = await api<{ node_id: string; metrics: NodeMetricSample[] }>(
          "GET",
          `/nodes/${activeNodeId}/metrics?limit=${limit}`
        );
        if (isSubscribed) {
          setMetrics(res.metrics || []);
          setError(null);
          setLastRefreshed(new Date());
          setIsLoading(false);
        }
      } catch (err: any) {
        if (isSubscribed) {
          setError(err.message || "Failed to load node telemetry");
          setIsLoading(false);
        }
      }
    };

    setIsLoading(true);
    fetchMetrics();

    // Poll every 4 seconds for live monitor updates
    const interval = setInterval(fetchMetrics, 4000);
    return () => {
      isSubscribed = false;
      clearInterval(interval);
    };
  }, [activeNodeId, timeRange]);

  // Formatted data for charts
  const chartData = useMemo(() => {
    return metrics.map((m) => {
      const d = new Date(m.timestamp * 1000);
      const timeStr = d.toTimeString().split(" ")[0];
      return {
        ...m,
        timeStr,
        memory_used_gib: Number((m.memory_used_mb / 1024).toFixed(2)),
        memory_total_gib: Number((m.memory_total_mb / 1024).toFixed(2)),
      };
    });
  }, [metrics]);

  // Summary statistics calculated strictly from actual samples
  const stats = useMemo(() => {
    if (metrics.length === 0) {
      return {
        currentCpu: activeNode?.cpu_percent ?? 0,
        peakCpu: activeNode?.cpu_percent ?? 0,
        avgCpu: activeNode?.cpu_percent ?? 0,
        currentMemPct: activeNode?.memory_percent ?? 0,
        currentMemUsedMb: activeNode?.memory_used_mb ?? 0,
        totalMemMb: activeNode?.memory_total_mb ?? 1,
        diskPercent: activeNode?.disk_percent ?? 0,
        diskUsedMb: activeNode?.disk_used_mb ?? 0,
        diskTotalMb: activeNode?.disk_total_mb ?? 1,
        rxKbps: activeNode?.network_rx_kbps ?? 0,
        txKbps: activeNode?.network_tx_kbps ?? 0,
      };
    }

    const cpuValues = metrics.map((m) => m.cpu_percent);
    const latest = metrics[metrics.length - 1];

    const currentCpu = latest.cpu_percent;
    const peakCpu = Math.max(...cpuValues);
    const avgCpu = Number(
      (cpuValues.reduce((a, b) => a + b, 0) / cpuValues.length).toFixed(1)
    );

    return {
      currentCpu,
      peakCpu,
      avgCpu,
      currentMemPct: latest.memory_percent,
      currentMemUsedMb: latest.memory_used_mb,
      totalMemMb: latest.memory_total_mb,
      diskPercent: latest.disk_percent,
      diskUsedMb: latest.disk_used_mb,
      diskTotalMb: latest.disk_total_mb,
      rxKbps: latest.network_rx_kbps,
      txKbps: latest.network_tx_kbps,
    };
  }, [metrics, activeNode]);

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Controls Bar: Node Selector + Time Range + Refresh */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "14px",
          padding: "16px 20px",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {showNodeSelector && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Target Node:</span>
              <div style={{ display: "flex", backgroundColor: "var(--bg-card)", padding: "3px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                {nodes.map((n) => {
                  const isSelected = n.id === activeNodeId;
                  const isHealthy = n.status === "HEALTHY";
                  return (
                    <button
                      key={n.id}
                      onClick={() => onSelectNode && onSelectNode(n.id)}
                      style={{
                        padding: "5px 12px",
                        fontSize: "12.5px",
                        fontWeight: 600,
                        borderRadius: "var(--radius-sm)",
                        border: "none",
                        backgroundColor: isSelected ? "var(--primary-subtle)" : "transparent",
                        color: isSelected ? "var(--primary)" : "var(--text-secondary)",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <span
                        style={{
                          width: "7px",
                          height: "7px",
                          borderRadius: "50%",
                          backgroundColor: isHealthy ? "var(--color-emerald-green)" : "var(--color-vermilion)",
                        }}
                      />
                      <span>{n.id}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Range:</span>
            <div style={{ display: "flex", backgroundColor: "var(--bg-card)", padding: "3px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              {(["5m", "15m", "30m", "1h"] as TimeRange[]).map((r) => (
                <button
                  key={r}
                  onClick={() => setTimeRange(r)}
                  style={{
                    padding: "4px 10px",
                    fontSize: "11.5px",
                    fontWeight: 600,
                    borderRadius: "var(--radius-sm)",
                    border: "none",
                    backgroundColor: timeRange === r ? "var(--primary-subtle)" : "transparent",
                    color: timeRange === r ? "var(--primary)" : "var(--text-muted)",
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12px", color: "var(--text-muted)" }}>
          <Clock size={14} />
          <span>
            {lastRefreshed ? `Live updated ${lastRefreshed.toTimeString().split(" ")[0]}` : "Awaiting data"}
          </span>
          <span style={{ padding: "2px 7px", borderRadius: "99px", backgroundColor: "var(--primary-subtle)", color: "var(--primary)", fontSize: "10.5px", fontWeight: 700 }}>
            {metrics.length} SAMPLES
          </span>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "14px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--danger-subtle)",
            color: "var(--danger)",
            fontSize: "13px",
          }}
        >
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Stats Bar for the selected node */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "14px" }}>
        {/* CPU Utilization */}
        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>CPU Utilization</span>
            <Cpu size={16} style={{ color: "var(--primary)" }} />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
            <span style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
              {stats.currentCpu}%
            </span>
            <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
              ({activeNode?.cpu_total || 0} cores)
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", display: "flex", gap: "8px" }}>
            <span>Peak: <strong>{stats.peakCpu}%</strong></span>
            <span>Avg: <strong>{stats.avgCpu}%</strong></span>
          </div>
        </div>

        {/* Memory Utilization */}
        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Memory Usage</span>
            <Activity size={16} style={{ color: "var(--accent-jade)" }} />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
            <span style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
              {stats.currentMemPct}%
            </span>
            <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
              {(stats.currentMemUsedMb / 1024).toFixed(1)} / {(stats.totalMemMb / 1024).toFixed(1)} GiB
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            Schedulable: <strong>{activeNode?.memory_schedulable_mb || 0} MiB</strong>
          </div>
        </div>

        {/* Disk Space */}
        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Root Storage</span>
            <HardDrive size={16} style={{ color: "var(--accent-violet)" }} />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
            <span style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
              {stats.diskPercent}%
            </span>
            <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
              {(stats.diskUsedMb / 1024).toFixed(1)} / {(stats.diskTotalMb / 1024).toFixed(1)} GiB
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            Free: <strong>{((stats.diskTotalMb - stats.diskUsedMb) / 1024).toFixed(1)} GiB</strong>
          </div>
        </div>

        {/* Network Throughput */}
        <div className="vc-stat-card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Network Rate</span>
            <Activity size={16} style={{ color: "var(--primary)" }} />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "3px" }}>
              <ArrowDownRight size={14} style={{ color: "var(--primary)" }} />
              <span style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {stats.rxKbps}
              </span>
              <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>KiB/s</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "3px" }}>
              <ArrowUpRight size={14} style={{ color: "var(--accent-violet)" }} />
              <span style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {stats.txKbps}
              </span>
              <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>KiB/s</span>
            </div>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            Workloads: <strong>{activeNode?.vms_running || 0} running microVMs</strong>
          </div>
        </div>
      </div>

      {/* Primary Graphs Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))", gap: "20px" }}>
        {/* Graph 1: CPU Utilization */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            padding: "22px 24px",
            boxShadow: "var(--shadow-sm)",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "8px",
                  backgroundColor: "var(--primary-subtle)",
                  color: "var(--primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Cpu size={16} />
              </div>
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  CPU Utilization History
                </h4>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Host total CPU percentage ({activeNode?.cpu_total || 0} logical cores)
                </span>
              </div>
            </div>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--primary)", fontFamily: "var(--font-mono)" }}>
              {stats.currentCpu}%
            </span>
          </div>

          <div style={{ height: "220px", width: "100%", marginTop: "6px" }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00D9FF" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#00D9FF" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(30, 45, 74, 0.45)" />
                  <XAxis dataKey="timeStr" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={11} tickLine={false} unit="%" />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload as NodeMetricSample & { timeStr: string };
                        return (
                          <div className="recharts-custom-tooltip">
                            <div style={{ fontWeight: 700, marginBottom: "4px" }}>{d.timeStr}</div>
                            <div style={{ color: "var(--primary)", fontWeight: 600 }}>CPU: {d.cpu_percent}%</div>
                            <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                              Running VMs: {d.vms_running}
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="cpu_percent"
                    stroke="#00D9FF"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#cpuGradient)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                Collecting CPU samples...
              </div>
            )}
          </div>
        </div>

        {/* Graph 2: Memory Utilization */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            padding: "22px 24px",
            boxShadow: "var(--shadow-sm)",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(24, 201, 167, 0.15)",
                  color: "var(--accent-jade)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Activity size={16} />
              </div>
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Memory Utilization History
                </h4>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Used vs Total physical memory (GiB)
                </span>
              </div>
            </div>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-jade)", fontFamily: "var(--font-mono)" }}>
              {stats.currentMemPct}%
            </span>
          </div>

          <div style={{ height: "220px", width: "100%", marginTop: "6px" }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#18C9A7" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#18C9A7" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(30, 45, 74, 0.45)" />
                  <XAxis dataKey="timeStr" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} unit="G" />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload as any;
                        return (
                          <div className="recharts-custom-tooltip">
                            <div style={{ fontWeight: 700, marginBottom: "4px" }}>{d.timeStr}</div>
                            <div style={{ color: "var(--accent-jade)", fontWeight: 600 }}>
                              Used: {d.memory_used_gib} GiB ({d.memory_percent}%)
                            </div>
                            <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                              Total: {d.memory_total_gib} GiB · Available: {d.memory_available_mb} MiB
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="memory_used_gib"
                    stroke="#18C9A7"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#memGradient)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                Collecting memory samples...
              </div>
            )}
          </div>
        </div>

        {/* Graph 3: Network Throughput Rates */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            padding: "22px 24px",
            boxShadow: "var(--shadow-sm)",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(147, 102, 241, 0.15)",
                  color: "var(--accent-violet)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Activity size={16} />
              </div>
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Network Traffic Rate
                </h4>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Throughput ingress (Rx) & egress (Tx) in KiB/s
                </span>
              </div>
            </div>
            <div style={{ display: "flex", gap: "10px", fontSize: "11px" }}>
              <span style={{ color: "var(--primary)" }}>● Rx</span>
              <span style={{ color: "var(--accent-violet)" }}>● Tx</span>
            </div>
          </div>

          <div style={{ height: "220px", width: "100%", marginTop: "6px" }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(30, 45, 74, 0.45)" />
                  <XAxis dataKey="timeStr" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload as NodeMetricSample & { timeStr: string };
                        return (
                          <div className="recharts-custom-tooltip">
                            <div style={{ fontWeight: 700, marginBottom: "4px" }}>{d.timeStr}</div>
                            <div style={{ color: "var(--primary)", fontWeight: 600 }}>Rx: {d.network_rx_kbps} KiB/s</div>
                            <div style={{ color: "var(--accent-violet)", fontWeight: 600 }}>Tx: {d.network_tx_kbps} KiB/s</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="network_rx_kbps"
                    name="Rx Rate"
                    stroke="#00D9FF"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="network_tx_kbps"
                    name="Tx Rate"
                    stroke="#9366F1"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                Calculating throughput rate...
              </div>
            )}
          </div>
        </div>

        {/* Graph 4: Workload Concurrency */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            padding: "22px 24px",
            boxShadow: "var(--shadow-sm)",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(0, 217, 255, 0.15)",
                  color: "var(--primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Layers size={16} />
              </div>
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Active MicroVM Instances
                </h4>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Running guest instances scheduled to this worker
                </span>
              </div>
            </div>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--primary)", fontFamily: "var(--font-mono)" }}>
              {activeNode?.vms_running || 0} active
            </span>
          </div>

          <div style={{ height: "220px", width: "100%", marginTop: "6px" }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(30, 45, 74, 0.45)" />
                  <XAxis dataKey="timeStr" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis allowDecimals={false} stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload as any;
                        return (
                          <div className="recharts-custom-tooltip">
                            <div style={{ fontWeight: 700, marginBottom: "4px" }}>{d.timeStr}</div>
                            <div style={{ color: "var(--primary)", fontWeight: 600 }}>Running VMs: {d.vms_running}</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="stepAfter"
                    dataKey="vms_running"
                    stroke="#00D9FF"
                    strokeWidth={2}
                    fillOpacity={0.2}
                    fill="#00D9FF"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                Tracking workload history...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
