import React, { useState, useEffect, useRef } from "react";
import { Icon } from "./Common";
import { request } from "../utils";
import type { SigningSessionInfo, SigningStatusInfo, SignatureInfo } from "../types";

interface SignDocumentSheetProps {
    documentId: number;
    documentTitle: string;
    onClose: () => void;
    onSigned: () => void;
}

export function SignDocumentSheet({ documentId, documentTitle, onClose, onSigned }: SignDocumentSheetProps) {
    const [step, setStep] = useState<"init" | "waiting" | "success" | "error">("init");
    const [signingSession, setSigningSession] = useState<SigningSessionInfo | null>(null);
    const [errorMsg, setErrorMsg] = useState("");
    const [isClosing, setIsClosing] = useState(false);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const close = () => {
        setIsClosing(true);
        if (pollRef.current) clearInterval(pollRef.current);
        setTimeout(() => {
            onClose();
        }, 300);
    };

    const initiateSign = async () => {
        try {
            setStep("waiting");
            const result = await request<SigningSessionInfo>("/edo/sign", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ document_id: documentId, signer_role: "sender" }),
            });
            setSigningSession(result);

            // Open eGov Mobile deeplink safely on iOS
            if (result.egov_mobile_link) {
                const link = result.egov_mobile_link;
                const tg = (window as any).Telegram?.WebApp;
                
                try {
                    // Method 1: Try native Telegram WebApp openLink first (if HTTPS)
                    if (tg && tg.openLink && link.startsWith("http")) {
                        tg.openLink(link, { try_instant_view: false });
                    } else {
                        // Method 2: Invisible Anchor Tag (best for custom schemes egovmobile:// on iOS)
                        const a = document.createElement("a");
                        a.href = link;
                        a.target = "_blank";
                        a.rel = "noopener noreferrer";
                        document.body.appendChild(a);
                        a.click();
                        setTimeout(() => document.body.removeChild(a), 100);
                    }
                } catch (e) {
                    // Method 3: Direct assignment fallback
                    window.location.href = link;
                }
            }

            // Start polling for signature
            pollRef.current = setInterval(async () => {
                try {
                    const status = await request<SigningStatusInfo>(
                        `/edo/signing-status/${result.signing_session_id}`
                    );
                    if (status.status === "signed") {
                        if (pollRef.current) clearInterval(pollRef.current);
                        setStep("success");
                        setTimeout(() => onSigned(), 1500);
                    } else if (status.status === "expired" || status.status === "error") {
                        if (pollRef.current) clearInterval(pollRef.current);
                        setStep("error");
                        setErrorMsg(status.status === "expired" ? "Время подписания истекло" : "Ошибка подписания");
                    }
                } catch {
                    // Ignore polling errors
                }
            }, 3000);
        } catch (err: any) {
            setStep("error");
            setErrorMsg(err.message || "Ошибка подключения к SIGEX");
        }
    };

    useEffect(() => {
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, []);

    return (
        <div
            style={{
                position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: "rgba(0,0,0,0.6)", zIndex: 1000,
                display: "flex", alignItems: "flex-end",
                backdropFilter: "blur(4px)",
                opacity: isClosing ? 0 : 1,
                transition: "opacity 0.3s ease",
            }}
            onClick={close}
        >
            <div
                className={isClosing ? "animate-slide-down" : "animate-slide-up"}
                style={{
                    width: "100%", background: "var(--card, #ffffff)",
                    borderTopLeftRadius: "24px", borderTopRightRadius: "24px",
                    padding: "16px 20px",
                    paddingBottom: "max(32px, env(safe-area-inset-bottom))",
                    boxShadow: "0 -8px 40px rgba(0,0,0,0.08)",
                }}
                onClick={e => e.stopPropagation()}
            >
                {/* Grabber */}
                <div style={{ width: "36px", height: "5px", borderRadius: "3px", backgroundColor: "var(--separator, #C7C7CC)", margin: "0 auto 16px" }} />

                {step === "init" && (
                    <>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
                            <div style={{
                                width: "48px", height: "48px", borderRadius: "14px",
                                background: "linear-gradient(135deg, #007AFF, #5856D6)",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                color: "#fff", flexShrink: 0,
                            }}>
                                <Icon name="verified" style={{ fontSize: "26px" }} />
                            </div>
                            <div>
                                <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 700, color: "var(--text, #1c1c1e)" }}>
                                    Подписать ЭЦП
                                </h3>
                                <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted, #8e8e93)" }}>
                                    {documentTitle}
                                </p>
                            </div>
                        </div>

                        <div style={{
                            background: "var(--segment-bg, #f2f2f7)", borderRadius: "14px",
                            padding: "14px 16px", margin: "16px 0",
                        }}>
                            <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                                <Icon name="info" style={{ fontSize: "20px", color: "var(--primary, #007AFF)", flexShrink: 0, marginTop: "1px" }} />
                                <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted, #8e8e93)", lineHeight: "1.5" }}>
                                    Документ будет подписан вашей ЭЦП через <strong style={{ color: "var(--text, #1c1c1e)" }}>eGov Mobile</strong>.
                                    Убедитесь, что приложение установлено и ключ ЭЦП загружен.
                                </p>
                            </div>
                        </div>

                        <button
                            onClick={initiateSign}
                            style={{
                                width: "100%", height: "52px", border: "none", borderRadius: "14px",
                                background: "linear-gradient(135deg, #007AFF, #5856D6)",
                                color: "#fff", fontSize: "17px", fontWeight: 600,
                                cursor: "pointer", display: "flex", alignItems: "center",
                                justifyContent: "center", gap: "10px",
                                boxShadow: "0 4px 16px rgba(0, 122, 255, 0.3)",
                            }}
                        >
                            <Icon name="draw" style={{ fontSize: "22px" }} />
                            Подписать через eGov Mobile
                        </button>
                    </>
                )}

                {step === "waiting" && (
                    <div style={{ textAlign: "center", padding: "24px 0" }}>
                        <div style={{
                            width: "64px", height: "64px", borderRadius: "50%",
                            background: "linear-gradient(135deg, rgba(0,122,255,0.1), rgba(88,86,214,0.1))",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            margin: "0 auto 16px",
                        }}>
                            <div className="spinner" style={{
                                width: "32px", height: "32px",
                                borderColor: "var(--primary, #007AFF)",
                                borderTopColor: "transparent",
                                borderWidth: "3px",
                            }} />
                        </div>
                        <h3 style={{ margin: "0 0 8px", fontSize: "18px", fontWeight: 700, color: "var(--text, #1c1c1e)" }}>
                            Ожидание подписи
                        </h3>
                        <p style={{ margin: 0, fontSize: "14px", color: "var(--text-muted, #8e8e93)", lineHeight: "1.5" }}>
                            Подтвердите подпись в приложении<br />
                            <strong style={{ color: "var(--text, #1c1c1e)" }}>eGov Mobile</strong>
                        </p>

                        {signingSession?.egov_mobile_link && (
                            <button
                                onClick={() => {
                                    const link = signingSession.egov_mobile_link;
                                    const tg = (window as any).Telegram?.WebApp;
                                    try {
                                        if (tg && tg.openLink && link.startsWith("http")) {
                                            tg.openLink(link, { try_instant_view: false });
                                        } else {
                                            const a = document.createElement("a");
                                            a.href = link;
                                            a.target = "_blank";
                                            a.rel = "noopener noreferrer";
                                            document.body.appendChild(a);
                                            a.click();
                                            setTimeout(() => document.body.removeChild(a), 100);
                                        }
                                    } catch (e) {
                                        window.location.href = link;
                                    }
                                }}
                                style={{
                                    marginTop: "20px", padding: "12px 24px",
                                    background: "var(--segment-bg, #f2f2f7)",
                                    border: "none", borderRadius: "12px",
                                    color: "var(--primary, #007AFF)",
                                    fontSize: "15px", fontWeight: 600, cursor: "pointer",
                                }}
                            >
                                Открыть eGov Mobile ещё раз
                            </button>
                        )}
                    </div>
                )}

                {step === "success" && (
                    <div style={{ textAlign: "center", padding: "24px 0" }}>
                        <div style={{
                            width: "64px", height: "64px", borderRadius: "50%",
                            background: "rgba(52, 199, 89, 0.1)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            margin: "0 auto 16px",
                        }}>
                            <Icon name="check_circle" style={{ fontSize: "36px", color: "#34C759" }} />
                        </div>
                        <h3 style={{ margin: "0 0 8px", fontSize: "18px", fontWeight: 700, color: "var(--text, #1c1c1e)" }}>
                            Документ подписан ✅
                        </h3>
                        <p style={{ margin: 0, fontSize: "14px", color: "var(--text-muted, #8e8e93)" }}>
                            ЭЦП успешно наложена
                        </p>
                    </div>
                )}

                {step === "error" && (
                    <div style={{ textAlign: "center", padding: "24px 0" }}>
                        <div style={{
                            width: "64px", height: "64px", borderRadius: "50%",
                            background: "rgba(255, 59, 48, 0.1)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            margin: "0 auto 16px",
                        }}>
                            <Icon name="error" style={{ fontSize: "36px", color: "#FF3B30" }} />
                        </div>
                        <h3 style={{ margin: "0 0 8px", fontSize: "18px", fontWeight: 700, color: "var(--text, #1c1c1e)" }}>
                            Ошибка подписания
                        </h3>
                        <p style={{ margin: "0 0 16px", fontSize: "14px", color: "var(--text-muted, #8e8e93)" }}>
                            {errorMsg}
                        </p>
                        <button
                            onClick={() => { setStep("init"); setErrorMsg(""); }}
                            style={{
                                padding: "12px 24px", background: "var(--segment-bg, #f2f2f7)",
                                border: "none", borderRadius: "12px",
                                color: "var(--primary, #007AFF)",
                                fontSize: "15px", fontWeight: 600, cursor: "pointer",
                            }}
                        >
                            Попробовать снова
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}


// ── EDO Status Badge Component ──

const EDO_STATUS_MAP: Record<string, { label: string; color: string; bg: string; icon: string }> = {
    draft:          { label: "Черновик",       color: "#8E8E93", bg: "rgba(142,142,147,0.12)", icon: "edit_note" },
    awaiting_sign:  { label: "Ожидает ЭЦП",   color: "#FF9500", bg: "rgba(255,149,0,0.12)",   icon: "draw" },
    signed_self:    { label: "Подписан вами",  color: "#007AFF", bg: "rgba(0,122,255,0.12)",   icon: "verified" },
    sent:           { label: "Отправлен",      color: "#5856D6", bg: "rgba(88,86,214,0.12)",   icon: "send" },
    signed_both:    { label: "Подписан",       color: "#34C759", bg: "rgba(52,199,89,0.12)",   icon: "task_alt" },
    rejected:       { label: "Отклонён",       color: "#FF3B30", bg: "rgba(255,59,48,0.12)",   icon: "cancel" },
    esf_pending:    { label: "Ожидание ЭСФ",   color: "#FF9500", bg: "rgba(255,149,0,0.12)",   icon: "schedule" },
    esf_submitted:  { label: "ЭСФ отправлена", color: "#34C759", bg: "rgba(52,199,89,0.12)",   icon: "receipt_long" },
    completed:      { label: "Завершён",       color: "#34C759", bg: "rgba(52,199,89,0.12)",   icon: "check_circle" },
};

interface EdoStatusBadgeProps {
    status: string;
    style?: React.CSSProperties;
}

export function EdoStatusBadge({ status, style }: EdoStatusBadgeProps) {
    const info = EDO_STATUS_MAP[status] || EDO_STATUS_MAP.draft;

    return (
        <span style={{
            display: "inline-flex", alignItems: "center", gap: "4px",
            padding: "3px 8px", borderRadius: "6px",
            background: info.bg, color: info.color,
            fontSize: "11px", fontWeight: 700,
            ...style,
        }}>
            <Icon name={info.icon} style={{ fontSize: "14px" }} />
            {info.label}
        </span>
    );
}


// ── Signature List Component ──

interface SignatureListProps {
    signatures: SignatureInfo[];
}

export function SignatureList({ signatures }: SignatureListProps) {
    if (!signatures.length) return null;

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {signatures.map((sig) => (
                <div
                    key={sig.id}
                    style={{
                        display: "flex", alignItems: "center", gap: "12px",
                        padding: "12px 14px", borderRadius: "14px",
                        background: "var(--segment-bg, #f2f2f7)",
                    }}
                >
                    <div style={{
                        width: "40px", height: "40px", borderRadius: "12px",
                        background: sig.signer_role === "sender"
                            ? "linear-gradient(135deg, rgba(0,122,255,0.15), rgba(88,86,214,0.15))"
                            : "linear-gradient(135deg, rgba(52,199,89,0.15), rgba(0,199,190,0.15))",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        flexShrink: 0,
                    }}>
                        <Icon
                            name="verified"
                            style={{
                                fontSize: "22px",
                                color: sig.signer_role === "sender" ? "#007AFF" : "#34C759",
                            }}
                        />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                            fontSize: "14px", fontWeight: 600,
                            color: "var(--text, #1c1c1e)",
                            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                        }}>
                            {sig.signer_name || sig.signer_iin}
                        </div>
                        <div style={{ fontSize: "12px", color: "var(--text-muted, #8e8e93)", marginTop: "2px" }}>
                            {sig.signer_role === "sender" ? "Отправитель" : "Получатель"} •{" "}
                            {sig.signed_at ? new Date(sig.signed_at).toLocaleString("ru-RU", {
                                day: "2-digit", month: "2-digit", year: "numeric",
                                hour: "2-digit", minute: "2-digit",
                            }) : "—"}
                        </div>
                        {sig.certificate_serial && (
                            <div style={{ fontSize: "10px", color: "var(--text-muted, #8e8e93)", marginTop: "2px", fontFamily: "monospace" }}>
                                Серт: {sig.certificate_serial.substring(0, 16)}...
                            </div>
                        )}
                    </div>
                    <Icon name="check_circle" style={{ fontSize: "20px", color: "#34C759", flexShrink: 0 }} />
                </div>
            ))}
        </div>
    );
}
