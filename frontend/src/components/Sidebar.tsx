import React from "react";
import {
  LayoutDashboard,
  Server,
  Cpu,
  Disc,
  Terminal,
  GitFork,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  CircleAlert,
  Compass,
} from "lucide-react";

export type NavTab =
  | "explore"
  | "overview"
  | "vms"
  | "nodes"
  | "images"
  | "terminals"
  | "decisions"
  | "events"
  | "settings";

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  isConnected: boolean;
  activeTerminalCount: number;
  totalVmCount: number;
  healthyNodeCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  collapsed,
  onToggleCollapse,
  isConnected,
  activeTerminalCount,
  totalVmCount,
  healthyNodeCount,
}) => {
  const navItems = [
    { id: "explore" as NavTab, label: "Explore Cluster", icon: Compass },
    { id: "overview" as NavTab, label: "Overview", icon: LayoutDashboard },
    { id: "vms" as NavTab, label: "Virtual Machines", icon: Server, badge: totalVmCount },
    { id: "nodes" as NavTab, label: "Nodes", icon: Cpu, badge: healthyNodeCount ? `${healthyNodeCount} OK` : undefined },
    { id: "images" as NavTab, label: "Images & OS", icon: Disc },
    { id: "terminals" as NavTab, label: "Terminals", icon: Terminal, badge: activeTerminalCount > 0 ? `${activeTerminalCount}` : undefined },
    { id: "decisions" as NavTab, label: "Placement Decisions", icon: GitFork },
    { id: "events" as NavTab, label: "Activity & Events", icon: Activity },
    { id: "settings" as NavTab, label: "Settings", icon: Settings },
  ];

  return (
    <aside
      style={{
        width: collapsed ? "72px" : "260px",
        backgroundColor: "var(--bg-sidebar)",
        color: "var(--sidebar-text)",
        borderRight: "1px solid var(--sidebar-border)",
        display: "flex",
        flexDirection: "column",
        transition: "width 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
        height: "100vh",
        position: "sticky",
        top: 0,
        zIndex: 30,
        flexShrink: 0,
        userSelect: "none",
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: collapsed ? "20px 14px" : "20px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "space-between",
          borderBottom: "1px solid var(--sidebar-border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", overflow: "hidden" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              backgroundColor: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFFFFF",
              flexShrink: 0,
              boxShadow: "0 2px 8px rgba(22, 138, 98, 0.35)",
            }}
          >
            <Server size={20} />
          </div>
          {!collapsed && (
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span
                style={{
                  fontWeight: 700,
                  fontSize: "16px",
                  letterSpacing: "-0.02em",
                  color: "var(--sidebar-text)",
                  whiteSpace: "nowrap",
                }}
              >
                VM Controller
              </span>
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--sidebar-muted)",
                  fontWeight: 500,
                  letterSpacing: "0.03em",
                  textTransform: "uppercase",
                }}
              >
                Hypervisor Manager
              </span>
            </div>
          )}
        </div>

        {!collapsed && (
          <button
            onClick={onToggleCollapse}
            title="Collapse sidebar"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--sidebar-muted)",
              padding: "4px",
              borderRadius: "6px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--sidebar-text)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--sidebar-muted)")}
          >
            <ChevronLeft size={18} />
          </button>
        )}
      </div>

      {/* Navigation Items */}
      <nav
        style={{
          flex: 1,
          padding: "16px 10px",
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          overflowY: "auto",
        }}
      >
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              title={collapsed ? item.label : undefined}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: collapsed ? "11px 0" : "10px 14px",
                justifyContent: collapsed ? "center" : "flex-start",
                borderRadius: "var(--radius-md)",
                backgroundColor: isActive ? "var(--sidebar-active)" : "transparent",
                color: isActive ? "#FFFFFF" : "var(--sidebar-muted)",
                border: "none",
                fontWeight: isActive ? 600 : 500,
                fontSize: "13.5px",
                position: "relative",
                transition: "all 0.15s ease",
                textAlign: "left",
                width: "100%",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "var(--sidebar-hover)";
                  e.currentTarget.style.color = "var(--sidebar-text)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.color = "var(--sidebar-muted)";
                }
              }}
            >
              {/* Active vertical pill indicator */}
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    left: "2px",
                    top: "8px",
                    bottom: "8px",
                    width: "3px",
                    borderRadius: "4px",
                    backgroundColor: "var(--primary)",
                  }}
                />
              )}

              <Icon
                size={19}
                style={{
                  color: isActive ? "var(--primary)" : "currentColor",
                  flexShrink: 0,
                }}
              />

              {!collapsed && (
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {item.label}
                </span>
              )}

              {!collapsed && item.badge !== undefined && (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    padding: "2px 7px",
                    borderRadius: "99px",
                    backgroundColor: isActive ? "rgba(22, 138, 98, 0.4)" : "rgba(255, 255, 255, 0.1)",
                    color: isActive ? "#FFFFFF" : "var(--sidebar-muted)",
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Status */}
      <div
        style={{
          padding: collapsed ? "14px 8px" : "14px 16px",
          borderTop: "1px solid var(--sidebar-border)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div
              style={{
                width: "9px",
                height: "9px",
                borderRadius: "50%",
                backgroundColor: isConnected ? "var(--primary)" : "var(--danger)",
                boxShadow: isConnected ? "0 0 8px var(--primary)" : "0 0 8px var(--danger)",
                flexShrink: 0,
              }}
            />
            {!collapsed && (
              <span style={{ fontSize: "12px", color: isConnected ? "#FFFFFF" : "var(--danger)", fontWeight: 500 }}>
                {isConnected ? "Controller Online" : "Disconnected"}
              </span>
            )}
          </div>

          {collapsed && (
            <button
              onClick={onToggleCollapse}
              title="Expand sidebar"
              style={{
                background: "transparent",
                border: "none",
                color: "var(--sidebar-muted)",
                padding: "4px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ChevronRight size={16} />
            </button>
          )}
        </div>

        {!collapsed && (
          <div
            style={{
              fontSize: "11px",
              color: "var(--sidebar-muted)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>v2.4 LTS</span>
            <span style={{ fontFamily: "var(--font-mono)", opacity: 0.8 }}>127.0.0.1:8000</span>
          </div>
        )}
      </div>
    </aside>
  );
};
