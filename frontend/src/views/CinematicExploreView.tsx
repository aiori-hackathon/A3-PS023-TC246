import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Server,
  Cpu,
  Layers,
  ArrowRight,
  Terminal,
  Activity,
  Plus,
  Compass,
  ArrowDown,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  ShieldCheck,
  Zap,
  LayoutDashboard,
  Sun,
  Moon,
  RotateCcw,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Node, VM, OSImage } from "../api";
import { ClusterScene } from "../components/ClusterScene";
import { NavTab } from "../components/Sidebar";

interface CinematicExploreViewProps {
  nodes: Node[];
  vms: VM[];
  images: OSImage[];
  isConnected: boolean;
  onNavigate: (tab: NavTab) => void;
  onOpenCreate: () => void;
  onOpenTerminal: (vm: VM) => void;
  theme?: "light" | "dark";
  onToggleTheme?: () => void;
  onOpenConnect?: () => void;
}

export const CinematicExploreView: React.FC<CinematicExploreViewProps> = ({
  nodes,
  vms,
  images,
  isConnected,
  onNavigate,
  onOpenCreate,
  onOpenTerminal,
  theme = "dark",
  onToggleTheme,
  onOpenConnect,
}) => {
  const [currentScene, setCurrentScene] = useState<number>(0);
  const [scrollProgress, setScrollProgress] = useState<number>(0);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedVmId, setSelectedVmId] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const touchStartYRef = useRef<number>(0);
  const isTransitioningRef = useRef(false);

  const totalScenes = 5;

  const nodeA = nodes.find((n) => n.id === "node-a") || nodes[0];
  const nodeB = nodes.find((n) => n.id === "node-b") || nodes[1];
  const runningVms = vms.filter((v) => v.status === "RUNNING");

  const prefersReducedMotion =
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Jump smoothly to a scene
  const goToScene = useCallback(
    (targetScene: number) => {
      const clamped = Math.max(0, Math.min(totalScenes - 1, targetScene));
      setCurrentScene(clamped);
      setScrollProgress(clamped);
    },
    [totalScenes]
  );

  // Natural Wheel scroll handler with dampening
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      // Prevent horizontal or micro-jitter
      if (Math.abs(e.deltaY) < 18) return;

      if (isTransitioningRef.current) return;

      if (e.deltaY > 0 && currentScene < totalScenes - 1) {
        isTransitioningRef.current = true;
        goToScene(currentScene + 1);
        setTimeout(() => {
          isTransitioningRef.current = false;
        }, 650);
      } else if (e.deltaY < 0 && currentScene > 0) {
        isTransitioningRef.current = true;
        goToScene(currentScene - 1);
        setTimeout(() => {
          isTransitioningRef.current = false;
        }, 650);
      }
    };

    window.addEventListener("wheel", handleWheel, { passive: true });
    return () => window.removeEventListener("wheel", handleWheel);
  }, [currentScene, totalScenes, goToScene]);

  // Touch gesture support
  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      touchStartYRef.current = e.touches[0].clientY;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const touchEndY = e.changedTouches[0].clientY;
      const deltaY = touchStartYRef.current - touchEndY;

      if (Math.abs(deltaY) > 40 && !isTransitioningRef.current) {
        if (deltaY > 0 && currentScene < totalScenes - 1) {
          isTransitioningRef.current = true;
          goToScene(currentScene + 1);
          setTimeout(() => {
            isTransitioningRef.current = false;
          }, 650);
        } else if (deltaY < 0 && currentScene > 0) {
          isTransitioningRef.current = true;
          goToScene(currentScene - 1);
          setTimeout(() => {
            isTransitioningRef.current = false;
          }, 650);
        }
      }
    };

    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchend", handleTouchEnd, { passive: true });
    return () => {
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("touchend", handleTouchEnd);
    };
  }, [currentScene, totalScenes, goToScene]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown" || e.key === "PageDown" || e.key === " ") {
        if (currentScene < totalScenes - 1) {
          e.preventDefault();
          goToScene(currentScene + 1);
        }
      } else if (e.key === "ArrowUp" || e.key === "PageUp") {
        if (currentScene > 0) {
          e.preventDefault();
          goToScene(currentScene - 1);
        }
      } else if (e.key === "Escape") {
        setSelectedNodeId(null);
        setSelectedVmId(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentScene, totalScenes, goToScene]);

  const sceneTitles = [
    { idx: 0, title: "Origin", desc: "Cobalt Glass Orchestrator Core" },
    { idx: 1, title: "Hosts", desc: "Jade & Amethyst Glass Nodes" },
    { idx: 2, title: "Fabric", desc: "Flowing Cyan Light Trails" },
    { idx: 3, title: "Workloads", desc: "Frosted Pearl MicroVM Topology" },
    { idx: 4, title: "Workspace", desc: "Operational Command Center" },
  ];

  return (
    <div
      ref={containerRef}
      style={{
        position: "relative",
        width: "100%",
        height: "100vh",
        overflow: "hidden",
        backgroundColor: "var(--bg-primary)",
      }}
    >
      {/* 3D Background Canvas responding to continuous progress and scene selection */}
      <ClusterScene
        nodes={nodes}
        vms={vms}
        selectedNodeId={selectedNodeId}
        selectedVmId={selectedVmId}
        onSelectNode={setSelectedNodeId}
        onSelectVm={setSelectedVmId}
        onOpenTerminal={onOpenTerminal}
        cinematicStage={currentScene}
        cinematicProgress={scrollProgress}
        isFullViewport={true}
      />

      {/* ======================================================== */}
      {/* 1. Restrained Floating Top Navigation Header              */}
      {/* ======================================================== */}
      <header
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "68px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 32px",
          zIndex: 30,
          pointerEvents: "auto",
        }}
      >
        {/* Brand Wordmark & Controller Status Pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            onClick={() => goToScene(0)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              cursor: "pointer",
              userSelect: "none",
            }}
          >
            <div
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "10px",
                backgroundColor: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#08090D",
                boxShadow: "0 0 20px rgba(0, 217, 255, 0.45)",
              }}
            >
              <Cpu size={19} />
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span
                style={{
                  fontSize: "15px",
                  fontWeight: 800,
                  letterSpacing: "-0.02em",
                  color: "var(--text-primary)",
                  fontFamily: "var(--font-heading)",
                }}
              >
                VM Controller
              </span>
              <span
                style={{
                  fontSize: "10px",
                  fontFamily: "var(--font-mono)",
                  color: "var(--primary)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Direct-Kernel Hypervisor
              </span>
            </div>
          </div>

          {/* Connection Status Pill */}
          <div
            onClick={onOpenConnect}
            title={isConnected ? "Controller is online and authenticated" : "Click to authenticate bearer token"}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "7px",
              padding: "5px 12px",
              borderRadius: "99px",
              backgroundColor: "rgba(16, 24, 39, 0.78)",
              border: `1px solid ${isConnected ? "rgba(0, 217, 255, 0.35)" : "var(--danger)"}`,
              backdropFilter: "blur(12px)",
              cursor: onOpenConnect ? "pointer" : "default",
              transition: "all 0.2s ease",
            }}
          >
            <div
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                backgroundColor: isConnected ? "var(--color-acid-lime)" : "var(--color-signal-coral)",
                boxShadow: isConnected ? "0 0 8px rgba(193, 255, 0, 0.85)" : "0 0 8px rgba(255, 76, 65, 0.85)",
              }}
            />
            <span
              style={{
                fontSize: "11px",
                fontFamily: "var(--font-mono)",
                color: isConnected ? "var(--text-primary)" : "var(--danger)",
                fontWeight: 500,
              }}
            >
              {isConnected ? "Controller Online" : "Disconnected"}
            </span>
          </div>
        </div>

        {/* Center: Restrained Floating Navigation Links */}
        <nav
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "5px 8px",
            borderRadius: "99px",
            backgroundColor: "rgba(16, 24, 39, 0.78)",
            border: "1px solid var(--border)",
            backdropFilter: "blur(14px)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <button
            onClick={() => goToScene(0)}
            style={{
              padding: "6px 14px",
              borderRadius: "99px",
              backgroundColor: "rgba(0, 217, 255, 0.15)",
              color: "var(--primary)",
              border: "1px solid rgba(0, 217, 255, 0.3)",
              fontSize: "12px",
              fontWeight: 700,
            }}
          >
            Explore
          </button>
          <button
            onClick={() => onNavigate("overview")}
            style={{
              padding: "6px 14px",
              borderRadius: "99px",
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              border: "none",
              fontSize: "12px",
              fontWeight: 500,
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
          >
            Overview
          </button>
          <button
            onClick={() => onNavigate("vms")}
            style={{
              padding: "6px 14px",
              borderRadius: "99px",
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              border: "none",
              fontSize: "12px",
              fontWeight: 500,
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
          >
            Virtual Machines ({vms.length})
          </button>
          <button
            onClick={() => onNavigate("nodes")}
            style={{
              padding: "6px 14px",
              borderRadius: "99px",
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              border: "none",
              fontSize: "12px",
              fontWeight: 500,
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
          >
            Nodes ({nodes.length})
          </button>
        </nav>

        {/* Right Action: Quick Actions & Skip to Dashboard */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {onToggleTheme && (
            <button
              onClick={onToggleTheme}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "rgba(16, 24, 39, 0.78)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                backdropFilter: "blur(12px)",
              }}
            >
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
          )}

          <button
            onClick={onOpenCreate}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 16px",
              borderRadius: "99px",
              backgroundColor: "rgba(0, 217, 255, 0.14)",
              border: "1px solid var(--primary)",
              color: "var(--primary)",
              fontSize: "12px",
              fontWeight: 700,
              backdropFilter: "blur(12px)",
              transition: "all 0.18s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "var(--primary)";
              e.currentTarget.style.color = "#08090D";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "rgba(0, 217, 255, 0.14)";
              e.currentTarget.style.color = "var(--primary)";
            }}
          >
            <Plus size={14} />
            <span>Create VM</span>
          </button>

          <button
            onClick={() => onNavigate("overview")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 18px",
              borderRadius: "99px",
              backgroundColor: "rgba(16, 24, 39, 0.88)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              fontSize: "12.5px",
              fontWeight: 600,
              backdropFilter: "blur(14px)",
              boxShadow: "var(--shadow-sm)",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--primary)";
              e.currentTarget.style.boxShadow = "var(--shadow-cyan-glow)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.boxShadow = "var(--shadow-sm)";
            }}
          >
            <span>Open Dashboard</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </header>

      {/* ======================================================== */}
      {/* 2. Floating Scene Index Stepper (Right Edge)             */}
      {/* ======================================================== */}
      <div
        style={{
          position: "absolute",
          right: "32px",
          top: "50%",
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          zIndex: 25,
          pointerEvents: "auto",
        }}
      >
        {sceneTitles.map((s) => {
          const isActive = currentScene === s.idx;
          return (
            <button
              key={s.idx}
              onClick={() => goToScene(s.idx)}
              title={`Scene 0${s.idx + 1}: ${s.title} — ${s.desc}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: "6px 4px",
                textAlign: "right",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "var(--font-mono)",
                    color: isActive ? "var(--primary)" : "var(--text-muted)",
                    fontWeight: isActive ? 700 : 500,
                    letterSpacing: "0.06em",
                    transition: "all 0.2s ease",
                  }}
                >
                  0{s.idx + 1}
                </span>
                <span
                  style={{
                    fontSize: "10px",
                    color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                    fontWeight: isActive ? 600 : 400,
                    opacity: isActive ? 1 : 0.6,
                    transition: "all 0.2s ease",
                  }}
                >
                  {s.title}
                </span>
              </div>
              <div
                style={{
                  width: isActive ? "26px" : "8px",
                  height: "3px",
                  borderRadius: "99px",
                  backgroundColor: isActive ? "var(--primary)" : "var(--border)",
                  boxShadow: isActive ? "0 0 12px rgba(0, 217, 255, 0.7)" : "none",
                  transition: "all 0.25s ease",
                }}
              />
            </button>
          );
        })}
      </div>

      {/* ======================================================== */}
      {/* 3. Narrative Story Overlays per Scene                    */}
      {/* ======================================================== */}
      <AnimatePresence mode="wait">
        {/* SCENE 1: Enter the World (Opening Experience) */}
        {currentScene === 0 && (
          <motion.div
            key="scene-0"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -18 }}
            transition={{ duration: 0.5 }}
            style={{
              position: "absolute",
              left: "48px",
              bottom: "72px",
              maxWidth: "660px",
              zIndex: 20,
              pointerEvents: "auto",
            }}
          >
            {/* Live Controller Connection Pill */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 14px",
                borderRadius: "99px",
                backgroundColor: "rgba(16, 24, 39, 0.8)",
                border: `1px solid ${isConnected ? "rgba(0, 217, 255, 0.4)" : "var(--border)"}`,
                backdropFilter: "blur(12px)",
                marginBottom: "20px",
              }}
            >
              <div
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor: isConnected ? "var(--color-acid-lime)" : "var(--color-signal-coral)",
                  boxShadow: isConnected ? "0 0 8px rgba(193, 255, 0, 0.85)" : "none",
                }}
              />
              <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontWeight: 500 }}>
                {isConnected ? "Controller Connected • Port 8000" : "Controller Disconnected"}
              </span>
            </div>

            <div className="hero-eyebrow" style={{ marginBottom: "14px" }}>
              <span>VIRTUAL INFRASTRUCTURE CONTROL</span>
            </div>

            <h1 className="hero-headline" style={{ marginBottom: "16px" }}>
              Your infrastructure,<br />
              <span style={{ color: "var(--primary)", textShadow: "0 0 28px rgba(0, 217, 255, 0.45)" }}>
                in your hands.
              </span>
            </h1>

            <p style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "28px", maxWidth: "540px" }}>
              Deploy, manage, and scale your virtual machines across your cluster. Explore the connected hypervisor topology in 3D and transition seamlessly into operational control.
            </p>

            <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
              <button
                onClick={() => goToScene(1)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "13px 26px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--primary)",
                  color: "#08090D",
                  fontSize: "14px",
                  fontWeight: 700,
                  boxShadow: "var(--shadow-cyan-glow)",
                  border: "none",
                  transition: "all 0.18s ease",
                }}
              >
                <span>Explore Cluster</span>
                <ChevronDown size={16} />
              </button>

              <button
                onClick={() => onNavigate("overview")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "13px 24px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "rgba(16, 24, 39, 0.78)",
                  color: "var(--text-primary)",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "1px solid var(--border)",
                  backdropFilter: "blur(14px)",
                  transition: "all 0.18s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--primary)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
              >
                <span>Open Dashboard</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </motion.div>
        )}

        {/* SCENE 2: Discover the Nodes */}
        {currentScene === 1 && (
          <motion.div
            key="scene-1"
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.5 }}
            style={{
              position: "absolute",
              left: "48px",
              top: "100px",
              maxWidth: "540px",
              zIndex: 20,
              pointerEvents: "auto",
            }}
          >
            <div className="hero-eyebrow" style={{ marginBottom: "10px" }}>
              <span>02 / HYPERVISOR NODES</span>
            </div>
            <h2 style={{ fontSize: "32px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)", marginBottom: "12px" }}>
              Two-Node Distributed Architecture
            </h2>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "22px" }}>
              The cluster coordinates execution across physical and nested virtualization environments, enforcing a dedicated 1024 MiB host safety reserve.
            </p>

            {/* Live Node Telemetry Badges */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
              {/* Node A Card */}
              {nodeA ? (
                <div
                  className="glass-panel"
                  onClick={() => setSelectedNodeId(nodeA.id)}
                  style={{
                    padding: "14px 18px",
                    borderRadius: "var(--radius-lg)",
                    borderLeft: "3px solid var(--accent-jade)",
                    cursor: "pointer",
                    transition: "all 0.18s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent-jade)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>{nodeA.id} (Jade Glass Host)</strong>
                      <span style={{ fontSize: "10.5px", padding: "1px 6px", borderRadius: "4px", backgroundColor: "rgba(24, 201, 167, 0.18)", color: "var(--accent-jade)" }}>
                        Direct KVM
                      </span>
                    </div>
                    <span style={{ fontSize: "11.5px", fontWeight: 700, color: nodeA.status === "HEALTHY" ? "var(--color-acid-lime)" : "var(--danger)" }}>
                      {nodeA.status}
                    </span>
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    {nodeA.memory_schedulable_mb} MiB Schedulable • {vms.filter((v) => v.node_id === nodeA.id).length} Active VMs
                  </div>
                </div>
              ) : (
                <div className="glass-panel" style={{ padding: "12px", color: "var(--text-muted)", fontSize: "12px" }}>
                  Awaiting Node A telemetry...
                </div>
              )}

              {/* Node B Card */}
              {nodeB ? (
                <div
                  className="glass-panel"
                  onClick={() => setSelectedNodeId(nodeB.id)}
                  style={{
                    padding: "14px 18px",
                    borderRadius: "var(--radius-lg)",
                    borderLeft: "3px solid var(--accent-violet)",
                    cursor: "pointer",
                    transition: "all 0.18s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent-violet)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>{nodeB.id} (Amethyst Glass Host)</strong>
                      <span style={{ fontSize: "10.5px", padding: "1px 6px", borderRadius: "4px", backgroundColor: "rgba(147, 102, 241, 0.18)", color: "var(--accent-violet)" }}>
                        Nested KVM
                      </span>
                    </div>
                    <span style={{ fontSize: "11.5px", fontWeight: 700, color: nodeB.status === "HEALTHY" ? "var(--color-acid-lime)" : "var(--danger)" }}>
                      {nodeB.status}
                    </span>
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    {nodeB.memory_schedulable_mb} MiB Schedulable • {vms.filter((v) => v.node_id === nodeB.id).length} Active VMs
                  </div>
                </div>
              ) : (
                <div className="glass-panel" style={{ padding: "12px", color: "var(--text-muted)", fontSize: "12px" }}>
                  Awaiting Node B telemetry...
                </div>
              )}
            </div>

            <button
              onClick={() => onNavigate("nodes")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 20px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(16, 24, 39, 0.78)",
                border: "1px solid var(--border)",
                color: "var(--primary)",
                fontSize: "13px",
                fontWeight: 600,
                backdropFilter: "blur(12px)",
                transition: "all 0.18s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
            >
              <span>Inspect Full Node Telemetry</span>
              <ArrowRight size={14} />
            </button>
          </motion.div>
        )}

        {/* SCENE 3: Follow the Connections */}
        {currentScene === 2 && (
          <motion.div
            key="scene-2"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -24 }}
            transition={{ duration: 0.5 }}
            style={{
              position: "absolute",
              left: "48px",
              bottom: "76px",
              maxWidth: "580px",
              zIndex: 20,
              pointerEvents: "auto",
            }}
          >
            <div className="hero-eyebrow" style={{ marginBottom: "10px" }}>
              <span>03 / NETWORK FABRIC</span>
            </div>
            <h2 style={{ fontSize: "32px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)", marginBottom: "12px" }}>
              Luminous Control Bus
            </h2>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "20px" }}>
              Controller communicates with hypervisor workers via authenticated bearer tokens over dedicated virtual bridge TAP pools:
            </p>

            <div
              className="glass-panel"
              style={{
                padding: "16px 20px",
                borderRadius: "var(--radius-lg)",
                marginBottom: "20px",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "14px",
                fontSize: "12.5px",
              }}
            >
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Host Virtual Bridge:</span>
                <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                  Host Bridge (192.168.100.0/24)
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Nested Inner Fabric:</span>
                <strong style={{ color: "var(--accent-violet)", fontFamily: "var(--font-mono)" }}>
                  10.77.0.0/24
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>TAP Interface Pool:</span>
                <strong style={{ color: "var(--primary)", fontFamily: "var(--font-mono)" }}>tapvm0 to tapvm7</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", display: "block" }}>Reconciliation Rate:</span>
                <strong style={{ color: "var(--color-acid-lime)" }}>5s Continuous Poll</strong>
              </div>
            </div>

            <button
              onClick={() => onNavigate("decisions")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 20px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(16, 24, 39, 0.78)",
                border: "1px solid var(--border)",
                color: "var(--primary)",
                fontSize: "13px",
                fontWeight: 600,
                backdropFilter: "blur(12px)",
                transition: "all 0.18s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
            >
              <span>Explore Scheduler Placement Log</span>
              <ArrowRight size={14} />
            </button>
          </motion.div>
        )}

        {/* SCENE 4: Explore the Virtual Machines */}
        {currentScene === 3 && (
          <motion.div
            key="scene-3"
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.5 }}
            style={{
              position: "absolute",
              left: "48px",
              top: "96px",
              maxWidth: "540px",
              zIndex: 20,
              pointerEvents: "auto",
            }}
          >
            <div className="hero-eyebrow" style={{ marginBottom: "10px" }}>
              <span>04 / MICROVM WORKLOADS</span>
            </div>
            <h2 style={{ fontSize: "32px", fontWeight: 800, color: "var(--text-primary)", fontFamily: "var(--font-heading)", marginBottom: "12px" }}>
              Live Instance Topology
            </h2>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "20px" }}>
              {vms.length > 0
                ? `${vms.length} microVM instances reside in the cluster, booted via direct kernel boot with zero process leaks.`
                : "No microVM instances are currently registered. The cluster is ready to schedule workloads."}
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "250px", overflowY: "auto", marginBottom: "22px" }}>
              {vms.slice(0, 4).map((vm) => (
                <div
                  key={vm.id}
                  className="glass-panel"
                  onClick={() => setSelectedVmId(vm.id)}
                  style={{
                    padding: "12px 16px",
                    borderRadius: "var(--radius-md)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    cursor: "pointer",
                    transition: "all 0.18s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--primary)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "13.5px", color: "var(--text-primary)" }}>{vm.name}</div>
                    <div style={{ fontSize: "11.5px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                      {vm.node_id} • {vm.vcpus} vCPU • {vm.memory_mb} MB • {vm.ip_address || "Pending IP"}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "99px",
                        backgroundColor: vm.status === "RUNNING" ? "rgba(193, 255, 0, 0.15)" : "rgba(146, 150, 168, 0.15)",
                        color: vm.status === "RUNNING" ? "var(--color-acid-lime)" : "var(--text-muted)",
                      }}
                    >
                      {vm.status}
                    </span>
                    {vm.status === "RUNNING" && vm.ip_address && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenTerminal(vm);
                        }}
                        title="Open SSH Console"
                        style={{
                          padding: "4px 8px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: "var(--primary-deep)",
                          border: "1px solid var(--primary)",
                          color: "#FFF",
                          fontSize: "11px",
                          fontWeight: 600,
                        }}
                      >
                        Terminal
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {vms.length === 0 && (
                <div className="glass-panel" style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                  Ready to provision your first microVM.
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={onOpenCreate}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "10px 20px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--primary)",
                  color: "#08090D",
                  fontSize: "13px",
                  fontWeight: 700,
                  border: "none",
                  boxShadow: "var(--shadow-cyan-glow)",
                }}
              >
                <Plus size={15} />
                <span>Provision VM</span>
              </button>
              <button
                onClick={() => onNavigate("vms")}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "10px 20px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "rgba(16, 24, 39, 0.78)",
                  border: "1px solid var(--border)",
                  color: "var(--text-primary)",
                  fontSize: "13px",
                  fontWeight: 600,
                  backdropFilter: "blur(12px)",
                }}
              >
                <span>View All VMs</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </motion.div>
        )}

        {/* SCENE 5: Enter the Operational Workspace */}
        {currentScene === 4 && (
          <motion.div
            key="scene-4"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.04 }}
            transition={{ duration: 0.5 }}
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "40px",
              zIndex: 20,
              backgroundColor: "rgba(10, 20, 40, 0.65)",
              backdropFilter: "blur(10px)",
              pointerEvents: "auto",
            }}
          >
            <div className="hero-eyebrow" style={{ marginBottom: "12px" }}>
              <span>05 / COMMAND & CONTROL</span>
            </div>
            <h2 className="hero-headline" style={{ textAlign: "center", marginBottom: "14px", fontSize: "44px" }}>
              Ready to Orchestrate Your Cluster.
            </h2>
            <p style={{ fontSize: "15px", color: "var(--text-secondary)", textAlign: "center", maxWidth: "560px", marginBottom: "36px" }}>
              Transition from cinematic exploration into the dedicated hypervisor management control center.
            </p>

            {/* Quick Launch Cards Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "16px",
                width: "100%",
                maxWidth: "960px",
                marginBottom: "32px",
              }}
            >
              {/* Overview */}
              <div
                className="glass-panel"
                onClick={() => onNavigate("overview")}
                style={{
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--primary)";
                  e.currentTarget.style.transform = "translateY(-3px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <Server size={22} style={{ color: "var(--primary)", marginBottom: "12px" }} />
                <h4 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Dashboard Overview
                </h4>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Cluster KPIs, memory allocation, and operational health.
                </p>
              </div>

              {/* Virtual Machines */}
              <div
                className="glass-panel"
                onClick={() => onNavigate("vms")}
                style={{
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--color-acid-lime)";
                  e.currentTarget.style.transform = "translateY(-3px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <Layers size={22} style={{ color: "var(--color-acid-lime)", marginBottom: "12px" }} />
                <h4 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Virtual Machines ({vms.length})
                </h4>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Lifecycle start/stop/delete operations and IP routing.
                </p>
              </div>

              {/* Terminals */}
              <div
                className="glass-panel"
                onClick={() => onNavigate("terminals")}
                style={{
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--accent-violet)";
                  e.currentTarget.style.transform = "translateY(-3px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <Terminal size={22} style={{ color: "var(--accent-violet)", marginBottom: "12px" }} />
                <h4 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Terminal Workspace
                </h4>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Interactive multi-session SSH console over WebSockets.
                </p>
              </div>

              {/* Provision VM */}
              <div
                className="glass-panel"
                onClick={onOpenCreate}
                style={{
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  cursor: "pointer",
                  border: "1px solid var(--primary)",
                  backgroundColor: "rgba(0, 217, 255, 0.08)",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-3px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <Plus size={22} style={{ color: "var(--primary)", marginBottom: "12px" }} />
                <h4 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Provision MicroVM
                </h4>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  5-step guided wizard with live scheduler reservation preview.
                </p>
              </div>
            </div>

            <button
              onClick={() => onNavigate("overview")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "13px 30px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--primary)",
                color: "#08090D",
                fontSize: "14px",
                fontWeight: 700,
                border: "none",
                boxShadow: "var(--shadow-cyan-glow)",
              }}
            >
              <span>Enter Operational Dashboard</span>
              <ArrowRight size={16} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bottom Scroll / Click to Advance Indicator (Shown on Scenes 1 to 4) */}
      {currentScene < totalScenes - 1 && (
        <div
          onClick={() => goToScene(currentScene + 1)}
          style={{
            position: "absolute",
            bottom: "22px",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "5px",
            cursor: "pointer",
            zIndex: 25,
            color: "var(--text-muted)",
            fontSize: "11.5px",
            fontFamily: "var(--font-mono)",
            opacity: 0.8,
            transition: "opacity 0.2s ease",
            pointerEvents: "auto",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.8")}
        >
          <span>SCROLL OR CLICK TO ADVANCE</span>
          <ArrowDown size={14} className="animate-bounce" />
        </div>
      )}
    </div>
  );
};
