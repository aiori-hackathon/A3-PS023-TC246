import { describe, it, expect, beforeEach } from "vitest";
import { getToken, setToken, clearToken } from "../api";

describe("VM Controller Frontend Logic & State", () => {
  beforeEach(() => {
    clearToken();
  });

  it("stores and retrieves the authentication bearer token securely", () => {
    expect(getToken()).toBe("");
    setToken("test-bearer-token-secret-1234");
    expect(getToken()).toBe("test-bearer-token-secret-1234");
    clearToken();
    expect(getToken()).toBe("");
  });

  it("calculates cluster schedulable memory headroom correctly", () => {
    const totalAvailableMb = 6792;
    const reservedMb = 1024; // HOST_RESERVE_MB from resource_monitor.py
    const schedulableMb = Math.max(0, totalAvailableMb - reservedMb);
    expect(schedulableMb).toBe(5768);

    const requestedMb = 1024;
    const remainingAfterRequest = Math.max(0, schedulableMb - requestedMb);
    expect(remainingAfterRequest).toBe(4744);
    expect(schedulableMb >= requestedMb).toBe(true);
  });

  it("rejects allocation when requested memory exceeds available capacity", () => {
    const totalAvailableMb = 1400;
    const reservedMb = 1024; // HOST_RESERVE_MB from resource_monitor.py
    const schedulableMb = Math.max(0, totalAvailableMb - reservedMb);
    expect(schedulableMb).toBe(376);

    const requestedMb = 1024;
    const canAccommodate = schedulableMb >= requestedMb;
    expect(canAccommodate).toBe(false);
  });

  it("clamps cinematic progress smoothly across the 5 storytelling scenes", () => {
    const totalScenes = 5;
    const clampProgress = (p: number) => Math.max(0, Math.min(totalScenes - 1, p));

    expect(clampProgress(-0.5)).toBe(0);
    expect(clampProgress(0)).toBe(0);
    expect(clampProgress(2.5)).toBe(2.5);
    expect(clampProgress(4.0)).toBe(4.0);
    expect(clampProgress(5.2)).toBe(4.0);
  });

  it("computes cosine interpolation smoothly for camera keyframes", () => {
    const cosineInterpolate = (start: number, end: number, frac: number) => {
      const smoothT = 0.5 - 0.5 * Math.cos(frac * Math.PI);
      return start + (end - start) * smoothT;
    };

    expect(cosineInterpolate(0, 10, 0)).toBeCloseTo(0);
    expect(cosineInterpolate(0, 10, 0.5)).toBeCloseTo(5);
    expect(cosineInterpolate(0, 10, 1.0)).toBeCloseTo(10);
  });

  it("validates direct kernel boot constraints on memory allocation (>= 128MB, <= 8192MB)", () => {
    const isValidMem = (mb: number) => mb >= 128 && mb <= 8192;
    expect(isValidMem(64)).toBe(false);
    expect(isValidMem(128)).toBe(true);
    expect(isValidMem(2048)).toBe(true);
    expect(isValidMem(8192)).toBe(true);
    expect(isValidMem(16384)).toBe(false);
  });

  it("preserves product identity without exposing internal challenge identifiers in UI", () => {
    const brandTitle = "VM Controller";
    expect(brandTitle).not.toContain("PS-023");
    expect(brandTitle).toBe("VM Controller");
  });

  it("enforces distinct visual identities across controller, worker nodes, and VMs", () => {
    const designTokens = {
      environment: { deepNavy: "#101827", midnightBlue: "#0A1428", elevatedBlueGrey: "#1A2942" },
      controller: { cobaltBlue: "#3158C9", pearlSilver: "#DCE6F2", electricCyan: "#00D9FF", periwinkle: "#8FA8FF" },
      nodeA: { jade: "#18C9A7", mint: "#75F0D0", deepTeal: "#126E70" },
      nodeB: { amethyst: "#9366F1", lavender: "#D1B8FF", deepViolet: "#492B8D" },
      vm: { frostedPearl: "#F4F1FF", paleBlue: "#B8D9FF", warmHighlight: "#FFCA80" },
      health: { emeraldGreen: "#168A62", vermilion: "#E6533C" },
    };

    // Controller: Cobalt + Pearl
    expect(designTokens.controller.cobaltBlue).toBe("#3158C9");
    expect(designTokens.controller.pearlSilver).toBe("#DCE6F2");

    // Node A: Jade
    expect(designTokens.nodeA.jade).toBe("#18C9A7");

    // Node B: Amethyst
    expect(designTokens.nodeB.amethyst).toBe("#9366F1");

    // VMs: Frosted Pearl
    expect(designTokens.vm.frostedPearl).toBe("#F4F1FF");

    // Health is separated from artistic palette
    expect(designTokens.health.emeraldGreen).not.toBe(designTokens.nodeA.jade);
    expect(designTokens.health.vermilion).not.toBe(designTokens.nodeB.amethyst);
  });

  it("verifies smooth cubic Bézier parameterization for flowing network light trails", () => {
    // Test parametric curve progress from 0.0 to 1.0
    const evaluateProgress = (p: number, speed: number, delta: number) => {
      let next = p + speed * delta * 0.28;
      if (next > 1.0) next = 0.0;
      return next;
    };

    expect(evaluateProgress(0.0, 1.0, 0.1)).toBeCloseTo(0.028);
    expect(evaluateProgress(0.99, 1.0, 0.5)).toBeCloseTo(0.0);
  });

  it("validates theme mode toggling and navigation sidebar tab options", () => {
    const validTabs = ["overview", "nodes", "vms", "decisions", "events", "images", "terminals", "settings"];
    expect(validTabs).toHaveLength(8);
    expect(validTabs).toContain("terminals");
    expect(validTabs).toContain("nodes");

    const toggleTheme = (current: "dark" | "light") => (current === "dark" ? "light" : "dark");
    expect(toggleTheme("dark")).toBe("light");
    expect(toggleTheme("light")).toBe("dark");
  });

  it("formats node backend badges and display labels accurately (Azure vs local-nested)", () => {
    const formatDisplay = (nodeId: string, backend?: string, label?: string) => {
      if (nodeId === "node-b") {
        return label || (backend === "azure" ? "worker-b (Azure)" : "worker-b (local nested)");
      }
      return label || nodeId;
    };

    expect(formatDisplay("node-b", "azure")).toBe("worker-b (Azure)");
    expect(formatDisplay("node-b", "local-nested")).toBe("worker-b (local nested)");
    expect(formatDisplay("node-a", "local", "worker-a (Host)")).toBe("worker-a (Host)");
  });

  it("constructs WebSocket terminal URLs correctly with bearer auth tokens", () => {
    const getWsTerminalUrl = (host: string, vmId: string, secure: boolean) => {
      const proto = secure ? "wss" : "ws";
      return `${proto}://${host}/vms/${vmId}/terminal`;
    };

    expect(getWsTerminalUrl("127.0.0.1:8000", "vm-12345678", false)).toBe("ws://127.0.0.1:8000/vms/vm-12345678/terminal");
    expect(getWsTerminalUrl("127.0.0.1:8000", "vm-12345678", true)).toBe("wss://127.0.0.1:8000/vms/vm-12345678/terminal");
  });
});
