import React from "react";
import {
  RefreshCw,
  Sun,
  Moon,
  KeyRound,
  Plus,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
} from "lucide-react";
import { NavTab } from "./Sidebar";

interface TopBarProps {
  currentTab: NavTab;
  isConnected: boolean;
  isRefreshing: boolean;
  lastUpdated: Date | null;
  onRefresh: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onOpenConnectModal: () => void;
  onOpenCreateModal: () => void;
  hasToken: boolean;
}

const tabTitles: Record<NavTab, { title: string; category: string }> = {
  explore: { title: "Cinematic Cluster Universe", category: "Experience" },
  overview: { title: "Overview", category: "Dashboard" },
  vms: { title: "Virtual Machines", category: "Compute" },
  nodes: { title: "Nodes", category: "Infrastructure" },
  images: { title: "Images & Operating Systems", category: "Storage" },
  terminals: { title: "Terminals Workspace", category: "Console" },
  decisions: { title: "Placement Decisions", category: "Scheduler" },
  events: { title: "Activity & Events", category: "Monitoring" },
  settings: { title: "Settings", category: "System" },
};

export const TopBar: React.FC<TopBarProps> = ({
  currentTab,
  isConnected,
  isRefreshing,
  lastUpdated,
  onRefresh,
  theme,
  onToggleTheme,
  onOpenConnectModal,
  onOpenCreateModal,
  hasToken,
}) => {
  const currentMeta = tabTitles[currentTab] || { title: "Dashboard", category: "VM Controller" };

  return (
    <header
      style={{
        height: "64px",
        backgroundColor: "var(--bg-surface)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 28px",
        position: "sticky",
        top: 0,
        zIndex: 20,
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Breadcrumb & Title */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "var(--text-muted)" }}>
          <span style={{ fontWeight: 500 }}>VM Controller</span>
          <ChevronRight size={14} />
          <span>{currentMeta.category}</span>
          <ChevronRight size={14} />
        </div>
        <h1
          style={{
            fontSize: "17px",
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "-0.01em",
            margin: 0,
          }}
        >
          {currentMeta.title}
        </h1>
      </div>

      {/* Right Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* Sync Status & Refresh */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "12.5px",
            color: "var(--text-muted)",
            padding: "4px 10px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "rgba(185, 177, 165, 0.08)",
          }}
        >
          {isConnected ? (
            <span style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--primary)" }}>
              <CheckCircle2 size={13} />
              <span>Synced {lastUpdated ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : "now"}</span>
            </span>
          ) : (
            <span style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--danger)" }}>
              <AlertCircle size={13} />
              <span>Offline</span>
            </span>
          )}

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Refresh state"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: isRefreshing ? "wait" : "pointer",
              padding: "2px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
          </button>
        </div>

        {/* API Token / Connect Status */}
        <button
          onClick={onOpenConnectModal}
          title={hasToken ? "API Token Configured" : "Enter API Token"}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "7px",
            padding: "7px 12px",
            borderRadius: "var(--radius-md)",
            border: `1px solid ${hasToken ? "var(--border)" : "var(--primary)"}`,
            backgroundColor: hasToken ? "var(--bg-surface)" : "var(--primary-subtle)",
            color: hasToken ? "var(--text-secondary)" : "var(--primary)",
            fontSize: "13px",
            fontWeight: 500,
          }}
        >
          <KeyRound size={15} />
          <span>{hasToken ? "Token Active" : "Connect Token"}</span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={onToggleTheme}
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border)",
            backgroundColor: "var(--bg-surface)",
            color: "var(--text-secondary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
        </button>

        {/* Quick Create VM */}
        <button
          onClick={onOpenCreateModal}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "8px 16px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--primary)",
            color: "#FFFFFF",
            border: "none",
            fontSize: "13px",
            fontWeight: 600,
            boxShadow: "0 2px 6px rgba(22, 138, 98, 0.25)",
          }}
        >
          <Plus size={16} />
          <span>Create VM</span>
        </button>
      </div>
    </header>
  );
};
