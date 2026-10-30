import React, { useState } from "react";
import {
  Settings,
  KeyRound,
  Shield,
  Server,
  RefreshCw,
  Moon,
  Sun,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Eye,
  Cpu,
} from "lucide-react";
import { getToken, clearToken } from "../api";
import { Node } from "../api";

interface SettingsViewProps {
  nodes: Node[];
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onOpenConnectModal: () => void;
  pollInterval: number;
  onChangePollInterval: (interval: number) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  nodes,
  theme,
  onToggleTheme,
  onOpenConnectModal,
  pollInterval,
  onChangePollInterval,
}) => {
  const currentToken = getToken();

  return (
    <div style={{ padding: "28px", maxWidth: "1000px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "22px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
          Settings & System Configuration
        </h2>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "2px" }}>
          Configure controller authentication, polling behavior, visual preferences, and cluster architecture
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* Authentication Card */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "14px" }}>
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
              <KeyRound size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                Controller API Token
              </h3>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Bearer token required for authenticated node queries, VM lifecycle, and console relays
              </p>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "14px 18px",
              backgroundColor: "var(--bg-card)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
            }}
          >
            <div>
              <span style={{ fontSize: "11.5px", color: "var(--text-muted)", display: "block" }}>Active Secret:</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "13.5px", color: "var(--text-primary)", letterSpacing: "0.15em" }}>
                {currentToken ? "••••••••••••••••••••••••••••••••" : "(No token configured)"}
              </span>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={onOpenConnectModal}
                style={{
                  padding: "7px 16px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--primary)",
                  backgroundColor: "var(--primary-subtle)",
                  color: "var(--primary)",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                {currentToken ? "Update Token" : "Enter Token"}
              </button>
            </div>
          </div>
        </div>

        {/* Polling & Refresh Interval */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "14px" }}>
            <div
              style={{
                width: "38px",
                height: "38px",
                borderRadius: "10px",
                backgroundColor: "rgba(182, 183, 172, 0.15)",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <RefreshCw size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                Telemetry Sync Frequency
              </h3>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Background polling interval for heartbeat updates and VM state reconciliation
              </p>
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            {[
              { label: "Every 3s", value: 3000 },
              { label: "Every 5s (Standard)", value: 5000 },
              { label: "Every 10s", value: 10000 },
              { label: "Every 30s", value: 30000 },
              { label: "Manual Only", value: 0 },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => onChangePollInterval(opt.value)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "var(--radius-md)",
                  border: `1.5px solid ${pollInterval === opt.value ? "var(--primary)" : "var(--border)"}`,
                  backgroundColor: pollInterval === opt.value ? "var(--primary-subtle)" : "var(--bg-card)",
                  color: pollInterval === opt.value ? "var(--primary)" : "var(--text-secondary)",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Appearance & Palette */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "38px",
                  height: "38px",
                  borderRadius: "10px",
                  backgroundColor: "rgba(182, 183, 172, 0.15)",
                  color: "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {theme === "light" ? <Sun size={20} /> : <Moon size={20} />}
              </div>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                  Theme & Visual Identity
                </h3>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Obsidian & Midnight with Laser Cyan (#00D9FF) and Cosmic Violet (#8832F7) accents
                </p>
              </div>
            </div>

            <button
              onClick={onToggleTheme}
              style={{
                padding: "8px 16px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
                fontSize: "13px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
              <span>{theme === "light" ? "Switch to Dark Palette" : "Switch to Light Palette"}</span>
            </button>
          </div>
        </div>

        {/* Cluster Infrastructure Profile */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
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
              <Cpu size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                Cluster Infrastructure Profile
              </h3>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Verified runtime parameters and virtualization backend details
              </p>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
              fontSize: "12.5px",
            }}
          >
            <div style={{ padding: "14px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Virtual Machine Monitor</span>
              <strong style={{ color: "var(--text-primary)" }}>Cloud Hypervisor (v54.0.0)</strong>
            </div>
            <div style={{ padding: "14px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Kernel Boot Method</span>
              <strong style={{ color: "var(--text-primary)" }}>Direct Kernel Boot (vmlinux-net.bin)</strong>
            </div>
            <div style={{ padding: "14px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Host Node Network</span>
              <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>192.168.100.0/24 (Host Bridge)</strong>
            </div>
            <div style={{ padding: "14px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Nested Node-B Network</span>
              <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>10.77.0.0/24 via 192.168.100.17</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
