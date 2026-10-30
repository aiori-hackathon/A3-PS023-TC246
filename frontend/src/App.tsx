import React, { useState, useEffect, useCallback } from "react";
import { Sidebar, NavTab } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { ConnectModal } from "./components/ConnectModal";
import { CreateVmModal } from "./components/CreateVmModal";

import { OverviewView } from "./views/OverviewView";
import { CinematicExploreView } from "./views/CinematicExploreView";
import { VmsView } from "./views/VmsView";
import { NodesView } from "./views/NodesView";
import { ImagesView } from "./views/ImagesView";
import { TerminalsView } from "./views/TerminalsView";
import { DecisionsView } from "./views/DecisionsView";
import { EventsView } from "./views/EventsView";
import { SettingsView } from "./views/SettingsView";

import { Node, VM, OSImage, Decision, EventItem, getToken, api } from "./api";

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>(() => {
    const hash = window.location.hash.replace(/^#\/?/, "").split("?")[0];
    const validTabs: NavTab[] = ["explore", "overview", "vms", "nodes", "images", "terminals", "decisions", "events", "settings"];
    if (validTabs.includes(hash as NavTab)) return hash as NavTab;
    return "explore";
  });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      const saved = localStorage.getItem("vmc_theme");
      if (saved === "light" || saved === "dark") return saved;
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    } catch {
      return "light";
    }
  });

  const [nodes, setNodes] = useState<Node[]>([]);
  const [vms, setVms] = useState<VM[]>([]);
  const [images, setImages] = useState<OSImage[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [activeTerminalCount, setActiveTerminalCount] = useState<number>(0);

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [terminalTargetVmId, setTerminalTargetVmId] = useState<string | null>(null);
  const [pollInterval, setPollInterval] = useState<number>(5000);

  // Apply theme class to document
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    try {
      localStorage.setItem("vmc_theme", theme);
    } catch {}
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  // Hash Routing
  const parseHash = useCallback(() => {
    const hash = window.location.hash.replace(/^#\/?/, "");
    if (!hash) return;

    const [tabPart, queryPart] = hash.split("?");
    const validTabs: NavTab[] = ["explore", "overview", "vms", "nodes", "images", "terminals", "decisions", "events", "settings"];
    if (validTabs.includes(tabPart as NavTab)) {
      setCurrentTab(tabPart as NavTab);
    }

    if (queryPart) {
      const params = new URLSearchParams(queryPart);
      const vmId = params.get("vm_id");
      if (vmId) {
        setTerminalTargetVmId(vmId);
      }
    }
  }, []);

  useEffect(() => {
    parseHash();
    window.addEventListener("hashchange", parseHash);
    return () => window.removeEventListener("hashchange", parseHash);
  }, [parseHash]);

  const navigateTo = (tab: NavTab, vmId?: string) => {
    setCurrentTab(tab);
    if (vmId) {
      setTerminalTargetVmId(vmId);
      window.location.hash = `#${tab}?vm_id=${vmId}`;
    } else {
      window.location.hash = `#${tab}`;
    }
  };

  // Main Fetch State
  const fetchData = useCallback(async () => {
    if (!getToken()) {
      setIsConnected(false);
      return;
    }

    setIsRefreshing(true);
    try {
      const [nodesData, vmsData, imagesData, decisionsData, eventsData] = await Promise.all([
        api<Node[]>("GET", "/nodes").catch(() => []),
        api<VM[]>("GET", "/vms").catch(() => []),
        api<OSImage[]>("GET", "/images").catch(() => []),
        api<Decision[]>("GET", "/decisions?limit=25").catch(() => []),
        api<EventItem[]>("GET", "/events?limit=50").catch(() => []),
      ]);

      setNodes(nodesData);
      setVms(vmsData);
      setImages(imagesData);
      setDecisions(decisionsData);
      setEvents(eventsData);
      setIsConnected(true);
      setLastUpdated(new Date());

      // Check active terminal sessions if available
      api<{ active_sessions: number }>("GET", "/terminal-sessions")
        .then((res) => setActiveTerminalCount(res.active_sessions || 0))
        .catch(() => {});
    } catch {
      setIsConnected(false);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Recurring Polling
  useEffect(() => {
    fetchData();
    if (pollInterval > 0) {
      const timer = setInterval(fetchData, pollInterval);
      return () => clearInterval(timer);
    }
  }, [fetchData, pollInterval]);

  const handleOpenTerminal = (vm: VM) => {
    navigateTo("terminals", vm.id);
  };

  const handleStartVm = async (vm: VM) => {
    try {
      await api("POST", `/vms/${vm.id}/start`);
      fetchData();
    } catch (err: any) {
      alert(`Start VM failed: ${err.message}`);
    }
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "var(--bg-primary)" }}>
      {currentTab === "explore" ? (
        <CinematicExploreView
          nodes={nodes}
          vms={vms}
          images={images}
          isConnected={isConnected}
          onNavigate={(tab) => navigateTo(tab)}
          onOpenCreate={() => setCreateModalOpen(true)}
          onOpenTerminal={handleOpenTerminal}
          theme={theme}
          onToggleTheme={toggleTheme}
          onOpenConnect={() => setConnectModalOpen(true)}
        />
      ) : (
        <div style={{ display: "flex", minHeight: "100vh" }}>
          {/* Persistent Sidebar */}
          <Sidebar
            currentTab={currentTab}
            onSelectTab={(tab) => navigateTo(tab)}
            collapsed={sidebarCollapsed}
            onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
            isConnected={isConnected}
            activeTerminalCount={activeTerminalCount}
            totalVmCount={vms.length}
            healthyNodeCount={nodes.filter((n) => n.status === "HEALTHY").length}
          />

          {/* Main Workspace */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflowY: "auto" }}>
            <TopBar
              currentTab={currentTab}
              isConnected={isConnected}
              isRefreshing={isRefreshing}
              lastUpdated={lastUpdated}
              onRefresh={fetchData}
              theme={theme}
              onToggleTheme={toggleTheme}
              onOpenConnectModal={() => setConnectModalOpen(true)}
              onOpenCreateModal={() => setCreateModalOpen(true)}
              hasToken={!!getToken()}
            />

            <main style={{ flex: 1, position: "relative" }}>
              {currentTab === "overview" && (
                <OverviewView
                  nodes={nodes}
                  vms={vms}
                  decisions={decisions}
                  events={events}
                  onOpenCreate={() => setCreateModalOpen(true)}
                  onNavigate={(tab) => navigateTo(tab)}
                  onOpenTerminal={handleOpenTerminal}
                />
              )}

              {currentTab === "vms" && (
                <VmsView
                  vms={vms}
                  nodes={nodes}
                  onRefresh={fetchData}
                  onOpenCreate={() => setCreateModalOpen(true)}
                  onOpenTerminal={handleOpenTerminal}
                />
              )}

              {currentTab === "nodes" && (
                <NodesView
                  nodes={nodes}
                  vms={vms}
                  events={events}
                  onOpenTerminal={handleOpenTerminal}
                />
              )}

              {currentTab === "images" && (
                <ImagesView
                  images={images}
                  vms={vms}
                  onRefresh={fetchData}
                />
              )}

              {currentTab === "terminals" && (
                <TerminalsView
                  vms={vms}
                  activeVmId={terminalTargetVmId}
                  onNavigateBack={() => navigateTo("overview")}
                  onStartVm={handleStartVm}
                />
              )}

              {currentTab === "decisions" && (
                <DecisionsView
                  decisions={decisions}
                />
              )}

              {currentTab === "events" && (
                <EventsView
                  events={events}
                />
              )}

              {currentTab === "settings" && (
                <SettingsView
                  nodes={nodes}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  onOpenConnectModal={() => setConnectModalOpen(true)}
                  pollInterval={pollInterval}
                  onChangePollInterval={setPollInterval}
                />
              )}
            </main>
          </div>
        </div>
      )}

      {/* Modals */}
      <ConnectModal
        isOpen={connectModalOpen}
        onClose={() => setConnectModalOpen(false)}
        onSuccess={fetchData}
      />

      <CreateVmModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={() => fetchData()}
        onOpenTerminal={handleOpenTerminal}
        nodes={nodes}
        images={images}
      />
    </div>
  );
};
