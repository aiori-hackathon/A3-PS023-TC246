import React, { useState } from "react";
import { KeyRound, Shield, Check, AlertCircle, X, Eye, EyeOff } from "lucide-react";
import { setToken, getToken, clearToken, api } from "../api";

interface ConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ConnectModal: React.FC<ConnectModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [tokenInput, setTokenInput] = useState(getToken());
  const [showToken, setShowToken] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) {
      setErrorMsg("Please enter an API token");
      return;
    }

    setIsVerifying(true);
    setErrorMsg(null);
    setToken(tokenInput.trim());

    try {
      await api("GET", "/nodes");
      setIsVerifying(false);
      onSuccess();
      onClose();
    } catch (err: any) {
      setIsVerifying(false);
      setErrorMsg(err.message || "Failed to authenticate with controller");
    }
  };

  const handleDisconnect = () => {
    clearToken();
    setTokenInput("");
    onSuccess();
    onClose();
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(32, 37, 34, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        className="animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "460px",
          backgroundColor: "var(--bg-surface)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-modal)",
          border: "1px solid var(--border)",
          padding: "24px",
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
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
              <h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>Controller Access</h2>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>Enter Bearer API Token to authenticate</p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleConnect}>
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, marginBottom: "6px", color: "var(--text-secondary)" }}>
              API Bearer Token
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showToken ? "text" : "password"}
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Paste Controller API Token here"
                autoComplete="off"
                style={{
                  width: "100%",
                  padding: "10px 40px 10px 12px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--bg-card)",
                  color: "var(--text-primary)",
                  fontSize: "13.5px",
                  fontFamily: "var(--font-mono)",
                }}
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                style={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  padding: "4px",
                }}
              >
                {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginTop: "6px" }}>
              Token is kept securely in browser session memory and sent only via standard Authorization headers.
            </p>
          </div>

          {errorMsg && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 12px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--danger-subtle)",
                color: "var(--danger)",
                fontSize: "12.5px",
                marginBottom: "16px",
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Buttons */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "20px" }}>
            {getToken() ? (
              <button
                type="button"
                onClick={handleDisconnect}
                style={{
                  padding: "8px 14px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  backgroundColor: "transparent",
                  color: "var(--danger)",
                  fontSize: "13px",
                  fontWeight: 500,
                }}
              >
                Disconnect
              </button>
            ) : <div />}

            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: "8px 14px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  fontSize: "13px",
                  fontWeight: 500,
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isVerifying}
                style={{
                  padding: "8px 18px",
                  borderRadius: "var(--radius-md)",
                  border: "none",
                  backgroundColor: "var(--primary)",
                  color: "#FFFFFF",
                  fontSize: "13px",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  cursor: isVerifying ? "wait" : "pointer",
                }}
              >
                {isVerifying ? (
                  <span>Verifying...</span>
                ) : (
                  <>
                    <Check size={16} />
                    <span>Connect</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
