import React, { useState } from "react";
import {
  Disc,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  Plus,
  Trash2,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  FolderOpen,
  Info,
  Copy,
  Check,
  Terminal,
} from "lucide-react";
import { OSImage, VM, api } from "../api";

interface ImagesViewProps {
  images: OSImage[];
  vms: VM[];
  onRefresh: () => void;
}

export const ImagesView: React.FC<ImagesViewProps> = ({ images, vms, onRefresh }) => {
  const [importOpen, setImportOpen] = useState(false);
  const [importId, setImportId] = useState("");
  const [importName, setImportName] = useState("");
  const [importDistro, setImportDistro] = useState("");
  const [importVersion, setImportVersion] = useState("");
  const [importPath, setImportPath] = useState("");
  const [importFormat, setImportFormat] = useState("raw");
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const [validatingId, setValidatingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [copiedCommandId, setCopiedCommandId] = useState<string | null>(null);

  const getDownloadCommand = (img: OSImage) => {
    if (!img.download_url) return "";
    if (img.download_url.endsWith(".raw")) {
      return `curl -L -o ~/ps023/images/${img.id}.raw "${img.download_url}"`;
    }
    if (img.download_url.endsWith(".qcow2")) {
      return `curl -L -o /tmp/${img.id}.qcow2 "${img.download_url}" && qemu-img convert -f qcow2 -O raw /tmp/${img.id}.qcow2 ~/ps023/images/${img.id}.raw && rm -f /tmp/${img.id}.qcow2`;
    }
    if (img.download_url.endsWith(".xz")) {
      return `curl -L -o /tmp/${img.id}.xz "${img.download_url}" && unxz /tmp/${img.id}.xz && mv /tmp/${img.id} ~/ps023/images/${img.id}.raw`;
    }
    return `curl -L -o ~/ps023/images/${img.id}.raw "${img.download_url}"`;
  };

  const handleCopyCommand = (img: OSImage) => {
    const cmd = getDownloadCommand(img);
    if (navigator.clipboard) {
      navigator.clipboard.writeText(cmd);
      setCopiedCommandId(img.id);
      setTimeout(() => setCopiedCommandId(null), 2500);
    }
  };

  const handleValidate = async (img: OSImage) => {
    setValidatingId(img.id);
    try {
      await api("POST", `/images/validate/${img.id}`);
      onRefresh();
    } catch (err: any) {
      alert(`Validation error: ${err.message}`);
    } finally {
      setValidatingId(null);
    }
  };

  const handleDelete = async (img: OSImage) => {
    // Check if any VM uses this image
    const inUse = vms.filter((v) => v.image === img.id);
    if (inUse.length > 0) {
      alert(`Cannot delete image '${img.name}': in use by ${inUse.length} active VM(s): ${inUse.map((v) => v.name).join(", ")}`);
      return;
    }

    if (!confirm(`Unregister OS image '${img.name}' (${img.id}) from the catalog?`)) return;

    try {
      await api("DELETE", `/images/${img.id}`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || "Failed to remove image");
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setImportLoading(true);
    setImportError(null);

    try {
      await api("POST", "/images/import", {
        id: importId.trim().toLowerCase(),
        name: importName.trim(),
        distro: importDistro.trim(),
        version: importVersion.trim(),
        path: importPath.trim(),
        format: importFormat,
      });
      setImportLoading(false);
      setImportOpen(false);
      onRefresh();
    } catch (err: any) {
      setImportLoading(false);
      setImportError(err.message || "Failed to import image");
    }
  };

  const formatSize = (bytes: number | null | undefined) => {
    if (!bytes) return "Unknown size";
    const gb = bytes / (1024 * 1024 * 1024);
    if (gb >= 1) return `${gb.toFixed(2)} GB`;
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(0)} MB`;
  };

  return (
    <div className="vc-page-container animate-fade-in">
      {/* Header */}
      <div className="vc-section-header">
        <div>
          <h2 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-heading)" }}>
            Images & Operating Systems
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--text-muted)", marginTop: "4px" }}>
            Selectable Linux distributions, verified RAW disk images, and hypervisor direct-kernel compatibility
          </p>
        </div>
        <button
          onClick={() => {
            setImportId("");
            setImportName("");
            setImportDistro("");
            setImportVersion("");
            setImportPath("");
            setImportError(null);
            setImportOpen(true);
          }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 18px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--primary)",
            color: "#0A1428",
            border: "none",
            fontSize: "13px",
            fontWeight: 700,
            boxShadow: "0 2px 8px rgba(0, 217, 255, 0.3)",
          }}
        >
          <Plus size={16} />
          <span>Import Custom Image</span>
        </button>
      </div>

      {/* Virtualization Details Note */}
      <div
        style={{
          display: "flex",
          gap: "14px",
          padding: "16px 20px",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-sm)",
          marginBottom: "28px",
        }}
      >
        <Info size={20} style={{ color: "var(--primary)", flexShrink: 0, marginTop: "2px" }} />
        <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
          <strong style={{ color: "var(--text-primary)" }}>Cloud Hypervisor Direct Boot Compatibility:</strong>
          {" "}This environment boots guests directly via uncompressed <code>vmlinux.bin</code> with{" "}
          <code>root=/dev/vda1 rw</code> and cloud-init <code>CIDATA</code> FAT seed image. Disk images must be RAW images
          with an ext4 root partition on <code>/dev/vda1</code>. Images marked <strong>Available</strong> are fully verified
          and ready for immediate provisioning.
        </div>
      </div>

      {/* OS Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
          gap: "20px",
          marginBottom: "32px",
        }}
      >
        {images.map((img) => {
          const isAvail = img.status === "AVAILABLE";
          const isMissing = img.status === "MISSING";
          const isValidating = validatingId === img.id;
          const dependentVms = vms.filter((v) => v.image === img.id);

          return (
            <div
              key={img.id}
              style={{
                backgroundColor: "var(--bg-surface)",
                borderRadius: "var(--radius-xl)",
                border: "1px solid var(--border)",
                padding: "22px",
                boxShadow: "var(--shadow-sm)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "16px",
              }}
            >
              <div>
                {/* Header */}
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div
                      style={{
                        width: "38px",
                        height: "38px",
                        borderRadius: "10px",
                        backgroundColor: isAvail ? "var(--primary-subtle)" : "rgba(185, 177, 165, 0.15)",
                        color: isAvail ? "var(--primary)" : "var(--text-muted)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Disc size={20} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>{img.name}</h3>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{img.version}</div>
                    </div>
                  </div>

                  {/* Status Pill */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "3px 8px",
                        borderRadius: "99px",
                        backgroundColor:
                          img.kernel_compat === "INCOMPATIBLE_BTRFS" || img.status === "INCOMPATIBLE_KERNEL"
                            ? "var(--warning-subtle)"
                            : isAvail
                            ? "rgba(22, 138, 98, 0.14)"
                            : isMissing
                            ? "var(--danger-subtle)"
                            : "rgba(185, 177, 165, 0.15)",
                        color:
                          img.kernel_compat === "INCOMPATIBLE_BTRFS" || img.status === "INCOMPATIBLE_KERNEL"
                            ? "var(--warning)"
                            : isAvail
                            ? "var(--color-emerald-green)"
                            : isMissing
                            ? "var(--danger)"
                            : "var(--text-muted)",
                      }}
                    >
                      {img.kernel_compat === "INCOMPATIBLE_BTRFS" ? "INCOMPATIBLE_KERNEL" : img.status}
                    </span>
                  </div>
                </div>

                {/* Details Breakdown */}
                <div
                  style={{
                    backgroundColor: "var(--bg-card)",
                    padding: "14px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border)",
                    fontSize: "12.5px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "7px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Format & Arch:</span>
                    <strong style={{ fontFamily: "var(--font-mono)", fontSize: "11.5px" }}>
                      {img.format.toUpperCase()} · {img.arch}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Hypervisor Boot:</span>
                    <strong style={{
                      fontSize: "11.5px",
                      color: img.kernel_compat === "COMPATIBLE" ? "var(--color-emerald-green)" : "var(--warning)"
                    }}>
                      {img.kernel_compat === "COMPATIBLE" ? "Direct Kernel (ext4)" : "Requires Btrfs Kernel"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Disk Size:</span>
                    <span>{formatSize(img.disk_size_bytes)}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Verification:</span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px", color: isAvail ? "var(--primary)" : "var(--text-secondary)" }}>
                      <ShieldCheck size={13} />
                      <span>{img.verification_status}</span>
                    </span>
                  </div>
                  {img.checksum && (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>Checksum:</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", color: "var(--text-muted)" }}>
                        {img.checksum.slice(0, 24)}...
                      </span>
                    </div>
                  )}
                  {img.notes && (
                    <div style={{ marginTop: "4px", padding: "8px 10px", borderRadius: "6px", backgroundColor: "rgba(0, 0, 0, 0.2)", fontSize: "11.5px", color: "var(--text-muted)", lineHeight: 1.4 }}>
                      {img.notes}
                    </div>
                  )}
                  {img.path && (
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: "2px" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>Path: </span>
                      <code style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{img.path}</code>
                    </div>
                  )}
                  {dependentVms.length > 0 && (
                    <div style={{ color: "var(--primary)", fontSize: "11.5px", fontWeight: 600, marginTop: "2px" }}>
                      In use by {dependentVms.length} VM(s) ({dependentVms.map((v) => v.name).join(", ")})
                    </div>
                  )}
                </div>

              </div>

              {/* Actions Footer */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  paddingTop: "12px",
                  borderTop: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() => handleValidate(img)}
                    disabled={isValidating}
                    style={{
                      padding: "5px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                      backgroundColor: "var(--bg-card)",
                      color: "var(--text-secondary)",
                      fontSize: "12px",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <RefreshCw size={12} className={isValidating ? "animate-spin" : ""} />
                    <span>Validate</span>
                  </button>

                  {img.download_url && !isAvail && (
                    <>
                      <a
                        href={img.download_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          padding: "5px 10px",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--border)",
                          backgroundColor: "var(--bg-card)",
                          color: "var(--text-primary)",
                          fontSize: "12px",
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          textDecoration: "none",
                        }}
                      >
                        <Download size={12} />
                        <span>Official Mirror</span>
                      </a>
                      <button
                        onClick={() => handleCopyCommand(img)}
                        title="Copy terminal command to download and convert image"
                        style={{
                          padding: "5px 10px",
                          borderRadius: "var(--radius-sm)",
                          border: `1px solid ${copiedCommandId === img.id ? "var(--color-acid-lime)" : "var(--border)"}`,
                          backgroundColor: "var(--bg-card)",
                          color: copiedCommandId === img.id ? "var(--color-acid-lime)" : "var(--text-primary)",
                          fontSize: "12px",
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        {copiedCommandId === img.id ? <Check size={12} /> : <Terminal size={12} />}
                        <span>{copiedCommandId === img.id ? "Copied!" : "CLI Setup"}</span>
                      </button>
                    </>
                  )}
                </div>

                {/* Delete button (prevented if default or in-use) */}
                {img.id !== "ubuntu-24-04" && (
                  <button
                    onClick={() => handleDelete(img)}
                    title="Remove from catalog"
                    style={{
                      padding: "5px 8px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                      backgroundColor: "var(--bg-card)",
                      color: "var(--danger)",
                      fontSize: "12px",
                    }}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Import Modal */}
      {importOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(32, 37, 34, 0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
          onClick={() => setImportOpen(false)}
        >
          <div
            className="animate-fade-in"
            style={{
              width: "100%",
              maxWidth: "520px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-xl)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-modal)",
              padding: "24px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
              Import Existing RAW Cloud Image
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--text-muted)", marginBottom: "16px" }}>
              Register a pre-built RAW disk image stored on the controller host
            </p>

            <form onSubmit={handleImportSubmit}>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "18px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Image Identifier * (e.g. debian-12-custom)
                  </label>
                  <input
                    type="text"
                    required
                    pattern="^[a-z0-9-]{2,32}$"
                    value={importId}
                    onChange={(e) => setImportId(e.target.value.toLowerCase())}
                    placeholder="debian-12-custom"
                    style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", fontSize: "13px" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Display Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={importName}
                    onChange={(e) => setImportName(e.target.value)}
                    placeholder="Debian 12 Bookworm (Custom)"
                    style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", fontSize: "13px" }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                      Distribution *
                    </label>
                    <input
                      type="text"
                      required
                      value={importDistro}
                      onChange={(e) => setImportDistro(e.target.value)}
                      placeholder="Debian"
                      style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", fontSize: "13px" }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                      Version *
                    </label>
                    <input
                      type="text"
                      required
                      value={importVersion}
                      onChange={(e) => setImportVersion(e.target.value)}
                      placeholder="12 (Bookworm)"
                      style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", fontSize: "13px" }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Absolute Host File Path * (.raw)
                  </label>
                  <input
                    type="text"
                    required
                    value={importPath}
                    onChange={(e) => setImportPath(e.target.value)}
                    placeholder="/var/lib/images/debian-12.raw"
                    style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", fontSize: "13px", fontFamily: "var(--font-mono)" }}
                  />
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "3px", display: "block" }}>
                    Must be a valid existing RAW image file.
                  </span>
                </div>
              </div>

              {importError && (
                <div
                  style={{
                    padding: "10px 12px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--danger-subtle)",
                    color: "var(--danger)",
                    fontSize: "12.5px",
                    marginBottom: "16px",
                  }}
                >
                  {importError}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setImportOpen(false)}
                  style={{
                    padding: "8px 16px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border)",
                    backgroundColor: "transparent",
                    color: "var(--text-secondary)",
                    fontSize: "13px",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importLoading}
                  style={{
                    padding: "8px 18px",
                    borderRadius: "var(--radius-md)",
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFFFFF",
                    fontSize: "13px",
                    fontWeight: 600,
                  }}
                >
                  {importLoading ? "Validating & Importing..." : "Register Image"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
