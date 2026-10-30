import React, { useState, useEffect } from "react";
import {
  X,
  Server,
  Cpu,
  HardDrive,
  Disc,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Info,
  Layers,
  Terminal,
  ShieldCheck,
  Check,
} from "lucide-react";
import { OSImage, Node, SchedulerPreviewResult, api } from "../api";

interface CreateVmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (vm: any) => void;
  onOpenTerminal?: (vm: any) => void;
  nodes: Node[];
  images: OSImage[];
}

export const CreateVmModal: React.FC<CreateVmModalProps> = ({
  isOpen,
  onClose,
  onCreated,
  onOpenTerminal,
  nodes,
  images,
}) => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);

  const [name, setName] = useState("");
  const [selectedImage, setSelectedImage] = useState<string>(() => {
    const ready = images.find((i) => i.status === "AVAILABLE" && i.kernel_compat !== "INCOMPATIBLE_BTRFS");
    return ready?.id || "ubuntu-24-04";
  });
  const [targetNode, setTargetNode] = useState<string>("auto");
  const [vcpus, setVcpus] = useState<number>(1);
  const [memoryMb, setMemoryMb] = useState<number>(1024);
  const [diskGb, setDiskGb] = useState<number>(4);

  const [preview, setPreview] = useState<SchedulerPreviewResult | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createdResult, setCreatedResult] = useState<any | null>(null);

  // Auto-set image if default not available or incompatible
  useEffect(() => {
    if (images.length > 0) {
      const cur = images.find((i) => i.id === selectedImage);
      if (!cur || cur.status !== "AVAILABLE" || cur.kernel_compat === "INCOMPATIBLE_BTRFS") {
        const firstReady = images.find((i) => i.status === "AVAILABLE" && i.kernel_compat !== "INCOMPATIBLE_BTRFS");
        if (firstReady) setSelectedImage(firstReady.id);
      }
    }
  }, [images, selectedImage]);

  // Request advisory scheduler preview when resources or target change
  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    setIsPreviewLoading(true);

    api<SchedulerPreviewResult>("POST", "/scheduler/preview", {
      memory_mb: memoryMb,
      vcpus: vcpus,
      target_node: targetNode === "auto" ? null : targetNode,
    })
      .then((res) => {
        if (active) {
          setPreview(res);
          setIsPreviewLoading(false);
        }
      })
      .catch(() => {
        if (active) setIsPreviewLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isOpen, memoryMb, vcpus, targetNode]);

  if (!isOpen) return null;

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const result = await api<any>("POST", "/vms", {
        name: name.trim().toLowerCase(),
        vcpus,
        memory_mb: memoryMb,
        disk_gb: diskGb,
        image: selectedImage,
        target_node: targetNode === "auto" ? null : targetNode,
      });

      setIsSubmitting(false);
      setCreatedResult(result);
      onCreated(result);
    } catch (err: any) {
      setIsSubmitting(false);
      setSubmitError(err.message || "Failed to create VM");
    }
  };

  const handleReset = () => {
    setName("");
    setCurrentStep(1);
    setCreatedResult(null);
    setSubmitError(null);
    onClose();
  };

  const currentImgObj = images.find((i) => i.id === selectedImage);
  const isImageAvailable =
    currentImgObj?.status === "AVAILABLE" &&
    currentImgObj?.kernel_compat !== "INCOMPATIBLE_BTRFS";

  const stepsList = [
    { num: 1, label: "OS & Image" },
    { num: 2, label: "Resources" },
    { num: 3, label: "Impact Preview" },
    { num: 4, label: "Review & Deploy" },
  ];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(20, 25, 23, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: "20px",
        overflowY: "auto",
      }}
      onClick={handleReset}
    >
      <div
        className="animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "800px",
          backgroundColor: "var(--bg-surface)",
          borderRadius: "var(--radius-xl)",
          boxShadow: "var(--shadow-modal)",
          border: "1px solid var(--border)",
          padding: "28px",
          position: "relative",
          maxHeight: "92vh",
          overflowY: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "12px",
                backgroundColor: "var(--primary-subtle)",
                color: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Server size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
                Provision Virtual Machine
              </h2>
              <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                Guided 5-step workflow with advisory scheduler reservation check
              </p>
            </div>
          </div>
          <button
            onClick={handleReset}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "6px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Wizard Stepper Bar (if not completed) */}
        {!createdResult && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "24px",
              padding: "12px 18px",
              backgroundColor: "var(--bg-card)",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--border)",
            }}
          >
            {stepsList.map((s, idx) => {
              const isActive = currentStep === s.num;
              const isPassed = currentStep > s.num;
              return (
                <React.Fragment key={s.num}>
                  <div
                    onClick={() => {
                      // allow jumping back or to step 2 if valid
                      if (isPassed || (s.num === 2 && isImageAvailable)) {
                        setCurrentStep(s.num as any);
                      }
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      cursor: isPassed ? "pointer" : "default",
                      opacity: isActive ? 1 : isPassed ? 0.85 : 0.45,
                    }}
                  >
                    <div
                      style={{
                        width: "24px",
                        height: "24px",
                        borderRadius: "50%",
                        backgroundColor: isActive
                          ? "var(--primary)"
                          : isPassed
                          ? "var(--primary-deep)"
                          : "var(--border)",
                        color: isActive || isPassed ? "#FFFFFF" : "var(--text-muted)",
                        fontSize: "12px",
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {isPassed ? <Check size={14} /> : s.num}
                    </div>
                    <span style={{ fontSize: "12.5px", fontWeight: isActive ? 700 : 500, color: isActive ? "var(--text-primary)" : "var(--text-muted)" }}>
                      {s.label}
                    </span>
                  </div>
                  {idx < stepsList.length - 1 && (
                    <div style={{ flex: 1, height: "1px", backgroundColor: "var(--border)", margin: "0 10px" }} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        )}

        {/* STEP 5: Success Screen */}
        {createdResult ? (
          <div style={{ padding: "20px 0", textAlign: "center" }}>
            <div
              style={{
                width: "60px",
                height: "60px",
                borderRadius: "50%",
                backgroundColor: "var(--primary-subtle)",
                color: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px",
              }}
            >
              <CheckCircle2 size={34} />
            </div>
            <h3 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)", marginBottom: "6px" }}>
              VM Created & Booted Successfully
            </h3>
            <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", marginBottom: "20px" }}>
              Machine <strong>{createdResult.name}</strong> was placed on node <strong>{createdResult.node_id}</strong>
            </p>

            <div
              style={{
                display: "inline-block",
                textAlign: "left",
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-lg)",
                padding: "16px 24px",
                marginBottom: "24px",
                minWidth: "340px",
                fontSize: "13px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ color: "var(--text-muted)" }}>VM Identifier:</span>
                <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{createdResult.id}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ color: "var(--text-muted)" }}>Assigned Node:</span>
                <span style={{ fontWeight: 600 }}>{createdResult.node_id}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ color: "var(--text-muted)" }}>Status:</span>
                <span style={{ color: "var(--primary)", fontWeight: 700 }}>{createdResult.status}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ color: "var(--text-muted)" }}>vCPU & RAM:</span>
                <span style={{ fontFamily: "var(--font-mono)" }}>
                  {createdResult.vcpus} vCPU · {createdResult.memory_mb} MB
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>IPv4 Address:</span>
                <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--primary)" }}>
                  {createdResult.ip_address || "DHCP Lease Pending"}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "center", gap: "12px" }}>
              <button
                onClick={handleReset}
                style={{
                  padding: "9px 20px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
              >
                Done
              </button>
              {onOpenTerminal && createdResult.ip_address && (
                <button
                  onClick={() => {
                    handleReset();
                    onOpenTerminal(createdResult);
                  }}
                  style={{
                    padding: "9px 22px",
                    borderRadius: "var(--radius-md)",
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFFFFF",
                    fontSize: "13px",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <Terminal size={16} />
                  <span>Launch Terminal</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div>
            {/* STEP 1: Choose Operating System */}
            {currentStep === 1 && (
              <div className="animate-fade-in">
                <div style={{ marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Step 1: Choose an Operating System Image
                  </h3>
                  <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                    Select a verified RAW disk image configured in the local image catalog
                  </p>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "14px", marginBottom: "24px" }}>
                  {images.map((img) => {
                    const isSelected = selectedImage === img.id;
                    const isAvail = img.status === "AVAILABLE";
                    const isIncompatible = img.kernel_compat === "INCOMPATIBLE_BTRFS" || img.status === "INCOMPATIBLE_KERNEL";
                    const isSelectable = isAvail && !isIncompatible;

                    return (
                      <div
                        key={img.id}
                        onClick={() => {
                          if (isSelectable) setSelectedImage(img.id);
                        }}
                        style={{
                          padding: "16px",
                          borderRadius: "var(--radius-lg)",
                          border: `1.5px solid ${isSelected ? "var(--primary)" : "var(--border)"}`,
                          backgroundColor: isSelected ? "var(--primary-subtle)" : "var(--bg-card)",
                          cursor: isSelectable ? "pointer" : "not-allowed",
                          opacity: isSelectable ? 1 : 0.65,
                          display: "flex",
                          flexDirection: "column",
                          gap: "8px",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                          <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                            {img.distro}
                          </span>
                          <span
                            style={{
                              fontSize: "10.5px",
                              fontWeight: 700,
                              padding: "2px 8px",
                              borderRadius: "99px",
                              backgroundColor: isSelectable
                                ? "rgba(22, 138, 98, 0.14)"
                                : isIncompatible
                                ? "var(--warning-subtle)"
                                : "rgba(182, 183, 172, 0.15)",
                              color: isSelectable
                                ? "var(--color-emerald-green)"
                                : isIncompatible
                                ? "var(--warning)"
                                : "var(--text-muted)",
                            }}
                          >
                            {isSelectable ? "Ready to Boot" : isIncompatible ? "Kernel Incompatible" : "Unavailable"}
                          </span>
                        </div>
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{img.version}</span>
                        {isIncompatible && (
                          <div style={{ fontSize: "11px", color: "var(--warning)", lineHeight: 1.4 }}>
                            Requires Btrfs kernel. Direct-boot kernel supports ext4.
                          </div>
                        )}
                        <div style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                          {img.format.toUpperCase()} · {img.arch} · {img.disk_size_bytes ? `${Math.round(img.disk_size_bytes / 1024 / 1024)} MB` : "Raw"}
                        </div>
                      </div>
                    );
                  })}
                </div>


                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    disabled={!isImageAvailable}
                    style={{
                      padding: "9px 20px",
                      borderRadius: "var(--radius-md)",
                      border: "none",
                      backgroundColor: "var(--primary)",
                      color: "#FFFFFF",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: isImageAvailable ? "pointer" : "not-allowed",
                      opacity: isImageAvailable ? 1 : 0.5,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span>Configure Resources</span>
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Configure Resources */}
            {currentStep === 2 && (
              <div className="animate-fade-in">
                <div style={{ marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Step 2: Configure VM Resources & Identity
                  </h3>
                  <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                    Specify instance name, vCPU count, memory allocation, and target node preference
                  </p>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                      VM Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                      placeholder="e.g. redis-prod-01"
                      pattern="^[a-z0-9][a-z0-9-]{0,30}$"
                      style={{
                        width: "100%",
                        padding: "9px 12px",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--border)",
                        backgroundColor: "var(--bg-card)",
                        color: "var(--text-primary)",
                        fontSize: "13.5px",
                      }}
                    />
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
                      1-31 lowercase alphanumeric chars and dashes.
                    </span>
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                      Placement Strategy
                    </label>
                    <select
                      value={targetNode}
                      onChange={(e) => setTargetNode(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "9px 12px",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--border)",
                        backgroundColor: "var(--bg-card)",
                        color: "var(--text-primary)",
                        fontSize: "13.5px",
                      }}
                    >
                      <option value="auto">Auto-Select (Recommended by Memory Capacity)</option>
                      {nodes.map((n) => (
                        <option key={n.id} value={n.id} disabled={n.status !== "HEALTHY"}>
                          {n.id} ({n.status}) - {n.memory_schedulable_mb} MB Schedulable
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Resource Sliders */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "14px", marginBottom: "24px" }}>
                  {/* vCPU */}
                  <div style={{ padding: "14px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--text-secondary)" }}>vCPU Cores</span>
                      <input
                        type="number"
                        min={1}
                        max={8}
                        value={vcpus}
                        onChange={(e) => setVcpus(Math.max(1, Math.min(8, parseInt(e.target.value) || 1)))}
                        style={{
                          width: "55px",
                          padding: "3px 6px",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--border)",
                          backgroundColor: "var(--bg-surface)",
                          color: "var(--text-primary)",
                          fontSize: "13px",
                          textAlign: "center",
                        }}
                      />
                    </div>
                    <input type="range" min={1} max={8} value={vcpus} onChange={(e) => setVcpus(parseInt(e.target.value))} />
                  </div>

                  {/* RAM */}
                  <div style={{ padding: "14px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--text-secondary)" }}>RAM (MiB)</span>
                      <input
                        type="number"
                        min={128}
                        max={8192}
                        step={128}
                        value={memoryMb}
                        onChange={(e) => setMemoryMb(Math.max(128, Math.min(8192, parseInt(e.target.value) || 128)))}
                        style={{
                          width: "70px",
                          padding: "3px 6px",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--border)",
                          backgroundColor: "var(--bg-surface)",
                          color: "var(--text-primary)",
                          fontSize: "13px",
                          textAlign: "center",
                        }}
                      />
                    </div>
                    <input type="range" min={128} max={8192} step={128} value={memoryMb} onChange={(e) => setMemoryMb(parseInt(e.target.value))} />
                  </div>

                  {/* Disk */}
                  <div style={{ padding: "14px", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--text-secondary)" }}>Disk (GiB)</span>
                      <input
                        type="number"
                        min={1}
                        max={50}
                        value={diskGb}
                        onChange={(e) => setDiskGb(Math.max(1, Math.min(50, parseInt(e.target.value) || 1)))}
                        style={{
                          width: "55px",
                          padding: "3px 6px",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--border)",
                          backgroundColor: "var(--bg-surface)",
                          color: "var(--text-primary)",
                          fontSize: "13px",
                          textAlign: "center",
                        }}
                      />
                    </div>
                    <input type="range" min={1} max={50} value={diskGb} onChange={(e) => setDiskGb(parseInt(e.target.value))} />
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(1)}
                    style={{
                      padding: "9px 18px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border)",
                      backgroundColor: "transparent",
                      color: "var(--text-secondary)",
                      fontSize: "13px",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <ArrowLeft size={15} />
                    <span>Back</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(3)}
                    disabled={!name.trim()}
                    style={{
                      padding: "9px 20px",
                      borderRadius: "var(--radius-md)",
                      border: "none",
                      backgroundColor: "var(--primary)",
                      color: "#FFFFFF",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: name.trim() ? "pointer" : "not-allowed",
                      opacity: name.trim() ? 1 : 0.5,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span>Preview Impact</span>
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Preview Resource Impact */}
            {currentStep === 3 && (
              <div className="animate-fade-in">
                <div style={{ marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Step 3: Advisory Scheduler Impact Preview
                  </h3>
                  <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                    Evaluate cluster memory headroom and proposed placement before atomic reservation
                  </p>
                </div>

                <div
                  style={{
                    backgroundColor: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-lg)",
                    padding: "18px",
                    marginBottom: "24px",
                  }}
                >
                  {preview ? (
                    <div>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          {preview.can_accommodate ? (
                            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--primary)", fontSize: "13.5px", fontWeight: 700 }}>
                              <CheckCircle2 size={18} />
                              <span>Placement Feasible</span>
                            </div>
                          ) : (
                            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--danger)", fontSize: "13.5px", fontWeight: 700 }}>
                              <AlertTriangle size={18} />
                              <span>Insufficient Schedulable Memory</span>
                            </div>
                          )}
                        </div>

                        {preview.recommended_node && (
                          <div style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                            Proposed Host: <strong style={{ color: "var(--primary)" }}>{preview.recommended_node}</strong> ({preview.reason})
                          </div>
                        )}
                      </div>

                      {/* Segmented Memory Bars for Candidate Nodes */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                        {preview.nodes.map((node) => {
                          const total = node.memory_total_mb || 1;
                          const resvPct = Math.min(100, (node.memory_reserved_mb / total) * 100);
                          const reqPct = Math.min(100 - resvPct, (memoryMb / total) * 100);
                          const freePct = Math.max(0, 100 - resvPct - reqPct);
                          const isTarget = preview.recommended_node === node.node_id;

                          return (
                            <div key={node.node_id} style={{ fontSize: "12.5px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                                <span style={{ fontWeight: isTarget ? 700 : 500, color: isTarget ? "var(--primary)" : "var(--text-primary)" }}>
                                  {node.node_id} {isTarget ? "★ Proposed Node" : ""}
                                </span>
                                <span style={{ color: "var(--text-muted)" }}>
                                  {node.memory_available_mb} MB available · {node.estimated_remaining_mb} MB remaining after boot
                                </span>
                              </div>

                              <div
                                style={{
                                  height: "10px",
                                  backgroundColor: "var(--border)",
                                  borderRadius: "5px",
                                  overflow: "hidden",
                                  display: "flex",
                                }}
                              >
                                <div style={{ width: `${resvPct}%`, backgroundColor: "#8832F7" }} title={`Reserved: ${node.memory_reserved_mb} MB`} />
                                <div style={{ width: `${reqPct}%`, backgroundColor: node.can_accommodate ? "#FFB800" : "var(--danger)" }} title={`Requested: ${memoryMb} MB`} />
                                <div style={{ width: `${freePct}%`, backgroundColor: "var(--primary)" }} title={`Free: ${node.estimated_remaining_mb} MB`} />
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <div style={{ display: "flex", gap: "18px", marginTop: "14px", fontSize: "11px", color: "var(--text-muted)" }}>
                        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                          <span style={{ width: "9px", height: "9px", borderRadius: "2px", backgroundColor: "#8832F7" }} />
                          Allocated Memory
                        </span>
                        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                          <span style={{ width: "9px", height: "9px", borderRadius: "2px", backgroundColor: "#E5AC44" }} />
                          New Allocation ({memoryMb} MiB)
                        </span>
                        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                          <span style={{ width: "9px", height: "9px", borderRadius: "2px", backgroundColor: "var(--primary)" }} />
                          Remaining Capacity
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: "13px", color: "var(--text-muted)", textAlign: "center", padding: "16px" }}>
                      Calculating advisory placement...
                    </div>
                  )}
                </div>

                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    style={{
                      padding: "9px 18px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border)",
                      backgroundColor: "transparent",
                      color: "var(--text-secondary)",
                      fontSize: "13px",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <ArrowLeft size={15} />
                    <span>Back</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(4)}
                    disabled={preview !== null && !preview.can_accommodate}
                    style={{
                      padding: "9px 20px",
                      borderRadius: "var(--radius-md)",
                      border: "none",
                      backgroundColor: "var(--primary)",
                      color: "#FFFFFF",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: preview?.can_accommodate ? "pointer" : "not-allowed",
                      opacity: preview?.can_accommodate ? 1 : 0.5,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span>Proceed to Review</span>
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: Review and Provision */}
            {currentStep === 4 && (
              <div className="animate-fade-in">
                <div style={{ marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Step 4: Review Deployment Specification
                  </h3>
                  <p style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
                    Confirm microVM parameters. The controller will execute an atomic reservation check.
                  </p>
                </div>

                <div
                  style={{
                    backgroundColor: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-lg)",
                    padding: "20px",
                    marginBottom: "20px",
                  }}
                >
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "13px" }}>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", marginBottom: "2px" }}>Name:</span>
                      <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>{name}</strong>
                    </div>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", marginBottom: "2px" }}>OS Image:</span>
                      <strong style={{ color: "var(--text-primary)" }}>{currentImgObj?.name || selectedImage}</strong>
                    </div>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", marginBottom: "2px" }}>Compute:</span>
                      <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                        {vcpus} vCPU · {memoryMb} MiB RAM · {diskGb} GiB Disk
                      </strong>
                    </div>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", marginBottom: "2px" }}>Assigned Host:</span>
                      <strong style={{ color: "var(--primary)" }}>
                        {preview?.recommended_node || (targetNode === "auto" ? "Scheduler Decided" : targetNode)}
                      </strong>
                    </div>
                  </div>
                </div>

                {submitError && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--danger-subtle)",
                      color: "var(--danger)",
                      fontSize: "13px",
                      marginBottom: "16px",
                    }}
                  >
                    <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                    <span>{submitError}</span>
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(3)}
                    style={{
                      padding: "9px 18px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border)",
                      backgroundColor: "transparent",
                      color: "var(--text-secondary)",
                      fontSize: "13px",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <ArrowLeft size={15} />
                    <span>Back</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSubmit()}
                    disabled={isSubmitting}
                    style={{
                      padding: "9px 24px",
                      borderRadius: "var(--radius-md)",
                      border: "none",
                      backgroundColor: "var(--primary)",
                      color: "#FFFFFF",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: isSubmitting ? "wait" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    {isSubmitting ? (
                      <>
                        <div className="animate-spin" style={{ width: "14px", height: "14px", border: "2px solid #FFF", borderTopColor: "transparent", borderRadius: "50%" }} />
                        <span>Provisioning & Booting...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={15} />
                        <span>Deploy MicroVM</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
