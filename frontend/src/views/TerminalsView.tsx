import React, { useState, useEffect, useRef } from "react";
import {
  Terminal as TerminalIcon,
  Plus,
  X,
  RefreshCw,
  Columns2,
  Rows2,
  Square,
  ArrowLeft,
  Server,
  Play,
  AlertCircle,
  CheckCircle2,
  Edit2,
  Check,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from "lucide-react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { VM, getToken } from "../api";

interface TerminalSession {
  id: string;
  vmId: string;
  vmName: string;
  vmIp: string;
  title: string;
}

interface TerminalsViewProps {
  vms: VM[];
  activeVmId?: string | null;
  onNavigateBack: () => void;
  onStartVm?: (vm: VM) => void;
}

// Single Terminal Instance Component
const TerminalPane: React.FC<{
  session: TerminalSession;
  vm: VM | undefined;
  fontSize: number;
  terminalTheme: "dark" | "light";
  onClose: () => void;
  onStartVm?: (vm: VM) => void;
}> = ({ session, vm, fontSize, terminalTheme, onClose, onStartVm }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const sockRef = useRef<WebSocket | null>(null);

  const [connState, setConnState] = useState<"connecting" | "connected" | "disconnected" | "error">("connecting");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [connectAttempts, setConnectAttempts] = useState(0);

  const isVmRunning = vm?.status === "RUNNING";
  const hasIp = !!vm?.ip_address;

  const startConnection = () => {
    if (!containerRef.current) return;
    if (sockRef.current) {
      try {
        sockRef.current.close();
      } catch {}
      sockRef.current = null;
    }

    if (!isVmRunning) {
      setConnState("error");
      setErrorMessage(`VM '${session.vmName}' is ${vm?.status || "STOPPED"}. Guest terminal requires the VM to be in RUNNING state.`);
      return;
    }

    if (!hasIp) {
      setConnState("error");
      setErrorMessage(`VM '${session.vmName}' has no IP address assigned yet. Please wait for network initialization.`);
      return;
    }

    setConnState("connecting");
    setErrorMessage(null);

    // Initialize xterm if not created
    if (!termRef.current) {
      const isDark = terminalTheme === "dark";
      const term = new Terminal({
        cursorBlink: true,
        fontSize,
        fontFamily: "'IBM Plex Mono', 'JetBrains Mono', ui-monospace, Menlo, Monaco, Consolas, monospace",
        theme: isDark
          ? {
              background: "#08090D",
              foreground: "#F0F1FA",
              cursor: "#00D9FF",
              cursorAccent: "#08090D",
              selectionBackground: "rgba(0, 217, 255, 0.35)",
              black: "#11131B",
              green: "#C1FF00",
              red: "#FF4C41",
              yellow: "#FFB800",
              blue: "#1A2FFB",
              white: "#F0F1FA",
            }
          : {
              background: "#FFFFFF",
              foreground: "#08090D",
              cursor: "#009EC2",
              cursorAccent: "#FFFFFF",
              selectionBackground: "rgba(0, 217, 255, 0.25)",
              black: "#08090D",
              green: "#009EC2",
              red: "#E6382E",
              yellow: "#D99800",
              blue: "#1A2FFB",
              white: "#F0F1FA",
            },
      });

      const fit = new FitAddon();
      term.loadAddon(fit);
      term.open(containerRef.current);
      fit.fit();

      termRef.current = term;
      fitRef.current = fit;

      term.onData((data) => {
        if (sockRef.current && sockRef.current.readyState === WebSocket.OPEN) {
          sockRef.current.send(JSON.stringify({ type: "input", data }));
        }
      });

      term.onResize((size) => {
        if (sockRef.current && sockRef.current.readyState === WebSocket.OPEN) {
          sockRef.current.send(JSON.stringify({ type: "resize", cols: size.cols, rows: size.rows }));
        }
      });
    } else {
      termRef.current.reset();
      fitRef.current?.fit();
    }

    const term = termRef.current;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${proto}//${host}/vms/${session.vmId}/terminal`;

    term.writeln(`\x1b[38;2;167;185;168m[Establishing secure SSH console to ${session.vmName} (${session.vmIp || "pending IP"})...]\x1b[0m`);

    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";
    sockRef.current = ws;

    ws.onopen = () => {
      setConnState("connected");
      ws.send(
        JSON.stringify({
          token: getToken(),
          cols: term.cols,
          rows: term.rows,
        })
      );
      term.focus();
    };

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        term.write(event.data);
      } else {
        term.write(new Uint8Array(event.data));
      }
    };

    ws.onclose = (event) => {
      setConnState("disconnected");
      const reason = event.reason || "Connection closed";
      term.writeln(`\r\n\x1b[38;2;230;83;60m[Disconnected: ${reason} (code: ${event.code})]\x1b[0m`);

      if (event.code === 4401) {
        setErrorMessage("Authentication failed: Invalid API Token. Please update your token via the Connect menu.");
      } else if (event.code === 4404) {
        setErrorMessage(`VM '${session.vmName}' is not running or has no IP address.`);
      } else if (event.code === 4502) {
        setErrorMessage(
          `Guest SSH connection failed: Port 22 is not reachable at ${session.vmIp}. Cloud-init guest initialization may still be in progress or sshd is not running.`
        );
      } else if (event.code === 4429) {
        setErrorMessage("Maximum concurrent terminal sessions exceeded (limit: 5 sessions).");
      }
    };

    ws.onerror = () => {
      setConnState("error");
    };
  };

  useEffect(() => {
    startConnection();
    return () => {
      if (sockRef.current) {
        try {
          sockRef.current.close();
        } catch {}
      }
      if (termRef.current) {
        termRef.current.dispose();
        termRef.current = null;
      }
    };
  }, [session.vmId, connectAttempts]);

  // Adjust theme dynamically
  useEffect(() => {
    if (termRef.current) {
      const isDark = terminalTheme === "dark";
      termRef.current.options.theme = isDark
        ? {
            background: "#08090D",
            foreground: "#F0F1FA",
            cursor: "#00D9FF",
            cursorAccent: "#08090D",
            selectionBackground: "rgba(0, 217, 255, 0.35)",
            black: "#11131B",
            green: "#C1FF00",
            red: "#FF4C41",
            yellow: "#FFB800",
            blue: "#1A2FFB",
            white: "#F0F1FA",
          }
        : {
            background: "#FFFFFF",
            foreground: "#08090D",
            cursor: "#009EC2",
            cursorAccent: "#FFFFFF",
            selectionBackground: "rgba(0, 217, 255, 0.25)",
            black: "#08090D",
            green: "#009EC2",
            red: "#E6382E",
            yellow: "#D99800",
            blue: "#1A2FFB",
            white: "#F0F1FA",
          };
    }
  }, [terminalTheme]);

  // Adjust font size dynamically
  useEffect(() => {
    if (termRef.current && fitRef.current) {
      termRef.current.options.fontSize = fontSize;
      fitRef.current.fit();
    }
  }, [fontSize]);

  // Window resize observer
  useEffect(() => {
    const handleResize = () => {
      fitRef.current?.fit();
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleClear = () => {
    termRef.current?.clear();
  };

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        backgroundColor: terminalTheme === "dark" ? "#161917" : "#FFFFFF",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        border: "1px solid var(--border)",
        position: "relative",
      }}
    >
      {/* Pane Action Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 14px",
          backgroundColor: terminalTheme === "dark" ? "var(--bg-card)" : "var(--bg-elevated)",
          borderBottom: "1px solid var(--border)",
          fontSize: "12.5px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor:
                connState === "connected"
                  ? "var(--primary)"
                  : connState === "connecting"
                  ? "var(--warning)"
                  : "var(--danger)",
            }}
          />
          <strong style={{ color: "var(--text-primary)" }}>{session.title}</strong>
          <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
            ({session.vmIp || "no IP"})
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            onClick={handleClear}
            title="Clear Terminal Output"
            style={{
              padding: "3px 8px",
              borderRadius: "4px",
              border: "1px solid var(--border)",
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              fontSize: "11px",
              fontWeight: 600,
            }}
          >
            Clear
          </button>
          <button
            onClick={() => setConnectAttempts((c) => c + 1)}
            title="Reconnect Session"
            style={{
              padding: "3px 8px",
              borderRadius: "4px",
              border: "1px solid var(--border)",
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              fontSize: "11px",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <RefreshCw size={11} />
            <span>Reconnect</span>
          </button>
        </div>
      </div>

      {/* Terminal Canvas Container */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          padding: "10px",
          overflow: "hidden",
          position: "relative",
        }}
      />

      {/* Diagnostic Overlay if not running or error */}
      {(!isVmRunning || errorMessage) && (
        <div
          style={{
            position: "absolute",
            bottom: "16px",
            left: "16px",
            right: "16px",
            padding: "14px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: isVmRunning ? "rgba(230, 83, 60, 0.92)" : "rgba(32, 37, 34, 0.92)",
            color: "#FFFFFF",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
            zIndex: 10,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
            <AlertCircle size={18} style={{ color: "#FFF", flexShrink: 0 }} />
            <div>
              <strong>Console Notice:</strong> {errorMessage || `VM '${session.vmName}' is currently STOPPED.`}
            </div>
          </div>

          {!isVmRunning && onStartVm && vm && (
            <button
              onClick={() => onStartVm(vm)}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius-sm)",
                border: "none",
                backgroundColor: "var(--primary)",
                color: "#FFFFFF",
                fontSize: "12px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "5px",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              <Play size={13} />
              <span>Start VM Now</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export const TerminalsView: React.FC<TerminalsViewProps> = ({
  vms,
  activeVmId,
  onNavigateBack,
  onStartVm,
}) => {
  const [sessions, setSessions] = useState<TerminalSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [splitMode, setSplitMode] = useState<"single" | "split">("single");
  const [fontSize, setFontSize] = useState<number>(14);
  const [terminalTheme, setTerminalTheme] = useState<"dark" | "light">("dark");
  const [editingTitleId, setEditingTitleId] = useState<string | null>(null);
  const [editingTitleVal, setEditingTitleVal] = useState("");

  const runningVms = vms.filter((v) => v.status === "RUNNING");

  // Create initial session if activeVmId is passed or none exist
  useEffect(() => {
    if (activeVmId) {
      const vm = vms.find((v) => v.id === activeVmId);
      if (vm) {
        const newSession: TerminalSession = {
          id: `session-${Date.now()}`,
          vmId: vm.id,
          vmName: vm.name,
          vmIp: vm.ip_address || "",
          title: `sh: ${vm.name}`,
        };
        setSessions((prev) => [...prev, newSession]);
        setActiveSessionId(newSession.id);
      }
    } else if (sessions.length === 0 && runningVms.length > 0) {
      const vm = runningVms[0];
      const newSession: TerminalSession = {
        id: `session-${Date.now()}`,
        vmId: vm.id,
        vmName: vm.name,
        vmIp: vm.ip_address || "",
        title: `sh: ${vm.name}`,
      };
      setSessions([newSession]);
      setActiveSessionId(newSession.id);
    }
  }, [activeVmId]);

  const handleAddSession = (vm: VM) => {
    const newSession: TerminalSession = {
      id: `session-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      vmId: vm.id,
      vmName: vm.name,
      vmIp: vm.ip_address || "",
      title: `sh: ${vm.name}`,
    };
    setSessions((prev) => [...prev, newSession]);
    setActiveSessionId(newSession.id);
  };

  const handleCloseSession = (id: string) => {
    const remaining = sessions.filter((s) => s.id !== id);
    setSessions(remaining);
    if (activeSessionId === id && remaining.length > 0) {
      setActiveSessionId(remaining[0].id);
    }
  };

  const handleRenameSave = (id: string) => {
    if (editingTitleVal.trim()) {
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, title: editingTitleVal.trim() } : s))
      );
    }
    setEditingTitleId(null);
  };

  const currentSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];
  const secondSession = sessions.length > 1 ? sessions.find((s) => s.id !== activeSessionId) : null;

  return (
    <div
      className="animate-fade-in"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 64px)",
        backgroundColor: "var(--bg-primary)",
      }}
    >
      {/* Top Workspace Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 24px",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <button
            onClick={onNavigateBack}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              fontSize: "12.5px",
              fontWeight: 600,
            }}
          >
            <ArrowLeft size={14} />
            <span>Return to Dashboard</span>
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <TerminalIcon size={18} style={{ color: "var(--primary)" }} />
            <h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>Terminal Workspace</h2>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                padding: "2px 7px",
                borderRadius: "99px",
                backgroundColor: "var(--primary-subtle)",
                color: "var(--primary)",
              }}
            >
              Real SSH PTY
            </span>
          </div>
        </div>

        {/* Global Terminal Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* Split Screen Toggle */}
          <button
            onClick={() => setSplitMode(splitMode === "single" ? "split" : "single")}
            title={splitMode === "single" ? "Split pane view" : "Single pane view"}
            disabled={sessions.length < 2}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              padding: "6px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border)",
              backgroundColor: splitMode === "split" ? "var(--primary-subtle)" : "var(--bg-card)",
              color: splitMode === "split" ? "var(--primary)" : "var(--text-secondary)",
              fontSize: "12px",
              fontWeight: 600,
              opacity: sessions.length < 2 ? 0.5 : 1,
            }}
          >
            <Columns2 size={14} />
            <span>Split Panes</span>
          </button>

          {/* Font Size */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-card)",
              overflow: "hidden",
            }}
          >
            <button
              onClick={() => setFontSize((s) => Math.max(11, s - 1))}
              title="Decrease font size"
              style={{ padding: "4px 8px", background: "transparent", border: "none", color: "var(--text-secondary)" }}
            >
              <ZoomOut size={13} />
            </button>
            <span style={{ fontSize: "11px", fontWeight: 600, padding: "0 4px", color: "var(--text-primary)" }}>
              {fontSize}px
            </span>
            <button
              onClick={() => setFontSize((s) => Math.min(22, s + 1))}
              title="Increase font size"
              style={{ padding: "4px 8px", background: "transparent", border: "none", color: "var(--text-secondary)" }}
            >
              <ZoomIn size={13} />
            </button>
          </div>

          {/* Theme selector */}
          <button
            onClick={() => setTerminalTheme(terminalTheme === "dark" ? "light" : "dark")}
            title="Toggle terminal dark/light background"
            style={{
              padding: "6px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
              color: "var(--text-secondary)",
              fontSize: "12px",
              fontWeight: 600,
            }}
          >
            {terminalTheme === "dark" ? "Theme: Dark" : "Theme: Light"}
          </button>
        </div>
      </div>

      {/* Main Body with Sidebar + Terminal Canvas */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Terminal Sessions Sidebar */}
        <div
          style={{
            width: "240px",
            backgroundColor: "var(--bg-surface)",
            borderRight: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            flexShrink: 0,
          }}
        >
          {/* Running VMs Picker */}
          <div style={{ padding: "14px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: "11.5px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
              Launch Guest Shell
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "160px", overflowY: "auto" }}>
              {vms.map((vm) => {
                const isRunning = vm.status === "RUNNING";
                return (
                  <button
                    key={vm.id}
                    onClick={() => handleAddSession(vm)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "6px 8px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                      backgroundColor: "var(--bg-card)",
                      color: "var(--text-primary)",
                      fontSize: "12px",
                      textAlign: "left",
                    }}
                  >
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      <strong style={{ fontSize: "12px" }}>{vm.name}</strong>
                      <div style={{ fontSize: "10.5px", color: "var(--text-muted)" }}>{vm.ip_address || "no IP"}</div>
                    </div>
                    <Plus size={14} style={{ color: "var(--primary)", flexShrink: 0 }} />
                  </button>
                );
              })}
              {vms.length === 0 && (
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>No VMs deployed</div>
              )}
            </div>
          </div>

          {/* Active Session List */}
          <div style={{ flex: 1, padding: "14px", overflowY: "auto" }}>
            <span style={{ fontSize: "11.5px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
              Active Sessions ({sessions.length})
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {sessions.map((s) => {
                const isActive = activeSessionId === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => setActiveSessionId(s.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "7px 10px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: isActive ? "var(--primary-subtle)" : "var(--bg-card)",
                      border: `1px solid ${isActive ? "var(--primary)" : "var(--border)"}`,
                      color: isActive ? "var(--primary)" : "var(--text-primary)",
                      cursor: "pointer",
                      fontSize: "12.5px",
                      fontWeight: isActive ? 600 : 500,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", overflow: "hidden" }}>
                      <TerminalIcon size={14} style={{ flexShrink: 0 }} />
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {s.title}
                      </span>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCloseSession(s.id);
                      }}
                      title="Close Tab"
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--text-muted)",
                        padding: "2px",
                      }}
                    >
                      <X size={13} />
                    </button>
                  </div>
                );
              })}

              {sessions.length === 0 && (
                <div style={{ fontSize: "12px", color: "var(--text-muted)", textAlign: "center", padding: "20px 0" }}>
                  No open sessions. Click a VM above to connect.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Terminal Workspace Area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "16px", gap: "12px", overflow: "hidden" }}>
          {/* Tab Bar */}
          {sessions.length > 0 && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center", overflowX: "auto" }}>
              {sessions.map((s) => {
                const isActive = activeSessionId === s.id;
                const isEditing = editingTitleId === s.id;

                return (
                  <div
                    key={s.id}
                    onClick={() => setActiveSessionId(s.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "6px 12px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: isActive ? "var(--bg-surface)" : "rgba(185, 177, 165, 0.12)",
                      border: `1px solid ${isActive ? "var(--border)" : "transparent"}`,
                      color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                      fontSize: "12.5px",
                      fontWeight: isActive ? 600 : 500,
                      cursor: "pointer",
                      boxShadow: isActive ? "var(--shadow-sm)" : "none",
                    }}
                  >
                    <TerminalIcon size={13} style={{ color: isActive ? "var(--primary)" : "inherit" }} />

                    {isEditing ? (
                      <input
                        type="text"
                        autoFocus
                        value={editingTitleVal}
                        onChange={(e) => setEditingTitleVal(e.target.value)}
                        onBlur={() => handleRenameSave(s.id)}
                        onKeyDown={(e) => e.key === "Enter" && handleRenameSave(s.id)}
                        style={{
                          fontSize: "12px",
                          padding: "1px 4px",
                          borderRadius: "3px",
                          border: "1px solid var(--primary)",
                          backgroundColor: "var(--bg-card)",
                          color: "var(--text-primary)",
                          width: "90px",
                        }}
                      />
                    ) : (
                      <span
                        onDoubleClick={() => {
                          setEditingTitleId(s.id);
                          setEditingTitleVal(s.title);
                        }}
                        title="Double-click to rename tab"
                      >
                        {s.title}
                      </span>
                    )}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCloseSession(s.id);
                      }}
                      title="Close"
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--text-muted)",
                        padding: "2px",
                      }}
                    >
                      <X size={12} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Panes Rendering */}
          {sessions.length > 0 ? (
            <div
              style={{
                flex: 1,
                display: "flex",
                gap: "12px",
                overflow: "hidden",
              }}
            >
              {currentSession && (
                <TerminalPane
                  key={currentSession.id}
                  session={currentSession}
                  vm={vms.find((v) => v.id === currentSession.vmId)}
                  fontSize={fontSize}
                  terminalTheme={terminalTheme}
                  onClose={() => handleCloseSession(currentSession.id)}
                  onStartVm={onStartVm}
                />
              )}

              {splitMode === "split" && secondSession && (
                <TerminalPane
                  key={secondSession.id}
                  session={secondSession}
                  vm={vms.find((v) => v.id === secondSession.vmId)}
                  fontSize={fontSize}
                  terminalTheme={terminalTheme}
                  onClose={() => handleCloseSession(secondSession.id)}
                  onStartVm={onStartVm}
                />
              )}
            </div>
          ) : (
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "var(--bg-surface)",
                borderRadius: "var(--radius-xl)",
                border: "1px solid var(--border)",
                padding: "40px",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  width: "56px",
                  height: "56px",
                  borderRadius: "16px",
                  backgroundColor: "var(--primary-subtle)",
                  color: "var(--primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "16px",
                }}
              >
                <TerminalIcon size={28} />
              </div>
              <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
                Dedicated Multi-Terminal Console
              </h3>
              <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", maxWidth: "480px", marginBottom: "20px" }}>
                Select a running virtual machine from the sidebar to establish an authenticated PTY SSH session directly into the guest instance.
              </p>
              {runningVms.length > 0 ? (
                <button
                  onClick={() => handleAddSession(runningVms[0])}
                  style={{
                    padding: "9px 20px",
                    borderRadius: "var(--radius-md)",
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFFFFF",
                    fontSize: "13px",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <Plus size={16} />
                  <span>Connect to {runningVms[0].name}</span>
                </button>
              ) : (
                <div style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                  No VMs currently running. Start a VM from the Virtual Machines page first.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
