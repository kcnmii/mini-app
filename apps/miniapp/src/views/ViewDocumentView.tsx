import React, { useState, useEffect } from "react";
import { Icon } from "../components/Common";
import { SignDocumentSheet, EdoStatusBadge, SignatureList } from "../components/EdoComponents";
import { formatMoney, request } from "../utils";
import type { InvoiceRecord, DocumentRecord, ShareInfo, SignatureInfo } from "../types";

interface ViewDocumentViewProps {
    setSubView: (v: any) => void;
    selectedInvoice: InvoiceRecord | undefined;
    selectedDoc: (DocumentRecord & { payload_json?: string }) | undefined;
    isPdfLoading: boolean;
    previewPages: string[];
    markInvoicePaid: (id: number) => void;
    markInvoiceSent: (id: number) => void;
    sendInvoice: () => void;
    sendReminder: (id: number) => void;
    generateDocument: (id: number, type: "act" | "waybill") => void;
    deleteInvoice: () => void;
    busy: string;
    animationType?: "none" | "left" | "up";
    refreshPreview?: (docId: number) => void;
    reloadDocuments?: () => void;
}

const IconButton = ({ icon, label, onClick, disabled, busy }: any) => (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px", opacity: disabled ? 0.3 : 1, pointerEvents: disabled ? "none" : "auto", cursor: "pointer", transition: "0.2s" }} onClick={onClick}>
        <div style={{ width: "52px", height: "52px", borderRadius: "18px", background: "var(--card, #f8f8fb)", display: "flex", justifyContent: "center", alignItems: "center", color: "var(--text, #1c1c1e)", border: "1px solid var(--separator, rgba(0,0,0,0.03))" }}>
            {busy ? <div className="spinner" style={{ borderColor: "var(--text, #1c1c1e)", borderTopColor: "transparent" }} /> : <Icon name={icon} style={{ fontSize: "24px" }} />}
        </div>
        <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text, #1c1c1e)" }}>{label}</span>
    </div>
);

const Switch = ({ checked, onChange, disabled }: any) => {
    return (
        <div
            onClick={(e) => { e.stopPropagation(); if (!disabled) onChange(!checked); }}
            style={{ width: "50px", height: "30px", borderRadius: "15px", background: checked ? "var(--ios-green, #34C759)" : "var(--segment-bg, #e5e5ea)", position: "relative", cursor: "pointer", transition: "0.3s", opacity: disabled ? 0.6 : 1 }}
        >
            <div style={{ width: "26px", height: "26px", borderRadius: "13px", background: "#fff", position: "absolute", top: "2px", left: checked ? "22px" : "2px", transition: "0.3s", boxShadow: "0 2px 4px rgba(0,0,0,0.2)" }} />
        </div>
    );
};

export function ViewDocumentView({
    setSubView,
    selectedInvoice,
    selectedDoc,
    isPdfLoading,
    previewPages,
    markInvoicePaid,
    markInvoiceSent,
    sendInvoice,
    sendReminder,
    generateDocument,
    deleteInvoice,
    busy,
    animationType = "left",
    refreshPreview,
    reloadDocuments,
}: ViewDocumentViewProps) {
    const [showDocMenu, setShowDocMenu] = useState(false);
    const [showActionsMenu, setShowActionsMenu] = useState(false);
    const [showDetails, setShowDetails] = useState(false);
    const [isClosingDetails, setIsClosingDetails] = useState(false);
    const [isClosingDocMenu, setIsClosingDocMenu] = useState(false);
    const [isClosingActions, setIsClosingActions] = useState(false);
    const [showSignSheet, setShowSignSheet] = useState(false);
    const [shareUrl, setShareUrl] = useState<string | null>(null);
    const [isSharing, setIsSharing] = useState(false);
    
    // EDO Signatures
    const [signatures, setSignatures] = useState<SignatureInfo[]>([]);
    const [isLoadingSignatures, setIsLoadingSignatures] = useState(false);

    // Auto-restore signing sheet if there's a pending session (after eGov Mobile redirect)
    useEffect(() => {
        const docId = (selectedInvoice as any)?.id || selectedDoc?.id;
        if (docId) {
            try {
                const saved = localStorage.getItem(`edo_signing_${docId}`);
                if (saved) {
                    const data = JSON.parse(saved);
                    const age = Date.now() - (data.timestamp || 0);
                    if (age < 10 * 60 * 1000 && data.sessionId) {
                        // There's a pending session — auto-open the sign sheet
                        setShowSignSheet(true);
                    }
                }
            } catch {}
        }
    }, [selectedDoc?.id, selectedInvoice]);

    useEffect(() => {
        if (showDetails && selectedDoc && selectedDoc.edo_status && selectedDoc.edo_status !== 'draft') {
            setIsLoadingSignatures(true);
            request<{signatures?: SignatureInfo[]}>(`/edo/document/${selectedDoc.id}/signatures`)
                .then(res => setSignatures(res.signatures || []))
                .catch(err => console.error("Failed to load signatures:", err))
                .finally(() => setIsLoadingSignatures(false));
        }
    }, [showDetails, selectedDoc?.id, selectedDoc?.edo_status]);

    // Polling for status updates (Rejected/Signed) when preview is open
    useEffect(() => {
        const docId = (selectedInvoice as any)?.id || selectedDoc?.id;
        if (!docId || showSignSheet) return; // Don't poll while signing sheet is open (it has its own poll)

        // Only poll for transient states
        const isTransient = selectedDoc?.edo_status === 'sent' || selectedDoc?.edo_status === 'signed_self';
        if (!isTransient) return;

        const interval = setInterval(async () => {
            try {
                // Fetch document details from backend to check for status change
                const isInv = !!selectedInvoice;
                const endpoint = isInv ? `/invoices/${docId}` : `/documents/${docId}`;
                const freshDoc = await request<any>(endpoint);
                
                if (freshDoc && freshDoc.edo_status !== selectedDoc?.edo_status) {
                    // Status changed! Refresh everything
                    if (refreshPreview) refreshPreview(docId);
                    if (reloadDocuments) reloadDocuments();
                }
            } catch (e) {
                console.error("Polling error:", e);
            }
        }, 5000); // Check every 5 seconds

        return () => clearInterval(interval);
    }, [selectedDoc?.id, selectedDoc?.edo_status, showSignSheet]);

    const closeDetails = () => {
        setIsClosingDetails(true);
        setTimeout(() => {
            setShowDetails(false);
            setIsClosingDetails(false);
        }, 300);
    };

    const closeDocMenu = () => {
        setIsClosingDocMenu(true);
        setTimeout(() => {
            setShowDocMenu(false);
            setIsClosingDocMenu(false);
        }, 300);
    };

    const closeActionsMenu = () => {
        setIsClosingActions(true);
        setTimeout(() => {
            setShowActionsMenu(false);
            setIsClosingActions(false);
        }, 150);
    };

    const animClass = animationType === "none" ? "" : animationType === "up" ? "animate-slide-up" : "animate-slide-left";

    const isNonInvoiceDoc = !selectedInvoice && !!selectedDoc;
    const title = selectedInvoice?.number ? `${selectedInvoice.number}` : (selectedDoc?.title || "");
    const status = selectedInvoice?.status || "document";
    const statusLabels: Record<string, string> = { draft: "Черновик", sent: "Отправлен", paid: "Оплачен", overdue: "Просрочен", document: "Архив" };
    const statusColors: Record<string, { bg: string, text: string }> = {
        draft: { bg: "#8E8E93", text: "#fff" },
        sent: { bg: "#FF9500", text: "#fff" },
        paid: { bg: "#34C759", text: "#fff" },
        overdue: { bg: "#FF3B30", text: "#fff" },
        document: { bg: "var(--separator, #E2E2E6)", text: "var(--text, #48484A)" }
    };

    // Doc type badge for non-invoice docs
    const getDocTypeBadge = (t: string): { code: string; color: string; bg: string } => {
        if (t.startsWith("Акт")) return { code: "АВР", color: "#34C759", bg: "rgba(52, 199, 89, 0.12)" };
        if (t.startsWith("Накладная")) return { code: "НКЛ", color: "#FF9500", bg: "rgba(255, 149, 0, 0.12)" };
        return { code: "ДОК", color: "var(--primary, #007AFF)", bg: "rgba(0, 122, 255, 0.12)" };
    };
    const docTypeBadge = isNonInvoiceDoc ? getDocTypeBadge(title) : null;
    const activeColor = statusColors[status] || statusColors.draft;

    const isPaid = status === "paid";

    return (
        <div className={animClass} style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", background: "var(--bg, #e5e5ea)", zIndex: 50, display: "flex", flexDirection: "column" }}>
            {/* Top Bar */}
            <div className="nav-bar" style={{ position: "relative", background: "var(--bg, #f2f2f7)", flexShrink: 0 }}>
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
                        <Icon name="chevron_left" />
                    </button>
                    <span className="nav-bar-title-center">{title}</span>
                    <div className="nav-bar-right">
                        <button className="nav-bar-btn-circle" onClick={() => setShowActionsMenu(true)}>
                            <Icon name="more_horiz" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Document Pages Container */}
            <div style={{ flex: 1, overflow: "auto", WebkitOverflowScrolling: "touch", padding: "16px", paddingBottom: "max(16px, env(safe-area-inset-bottom))", touchAction: "pan-x pan-y pinch-zoom", position: "relative" }}>
                {previewPages.length === 0 && (
                    <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", display: "flex", justifyContent: "center", alignItems: "center" }}>
                        {isPdfLoading ? (
                            <div className="spinner" style={{ width: "32px", height: "32px", borderColor: "var(--primary, #007AFF)", borderTopColor: "transparent", borderWidth: "3px" }} />
                        ) : (
                            <div style={{ color: "var(--text-muted, #8e8e93)", fontWeight: 500 }}>
                                Нет превью
                            </div>
                        )}
                    </div>
                )}
                {previewPages.length > 0 && previewPages.map((src, i) => (
                    <img key={i} src={src} alt={`Page ${i + 1}`} style={{ width: "100%", borderRadius: "8px", boxShadow: "0 2px 10px rgba(0,0,0,0.1)", marginBottom: "16px", display: "block" }} />
                ))}
            </div>

            {/* Floating 'Подробнее' Button */}
            <div style={{ position: "fixed", bottom: "max(16px, env(safe-area-inset-bottom))", left: "0", right: "0", display: "flex", justifyContent: "center", zIndex: 60, pointerEvents: "none" }}>
                <button 
                    className="nav-bar-pill-btn"
                    onClick={() => setShowDetails(true)} 
                    style={{ pointerEvents: "auto", height: "40px" }}
                >
                    Подробнее
                    <Icon name="keyboard_arrow_up" style={{ fontSize: "18px", opacity: 0.9 }} />
                </button>
            </div>

            {/* Details Modal */}
            {(showDetails || isClosingDetails) && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.6)", zIndex: 900, display: "flex", alignItems: "flex-end", backdropFilter: "blur(4px)", opacity: isClosingDetails ? 0 : 1, transition: "opacity 0.3s ease" }} onClick={closeDetails}>
                    <div className={isClosingDetails ? "animate-slide-down" : "animate-slide-up"} style={{ width: "100%", background: "var(--card, #ffffff)", borderTopLeftRadius: "24px", borderTopRightRadius: "24px", padding: "16px 20px", paddingBottom: "max(24px, env(safe-area-inset-bottom))", boxShadow: "0 -8px 40px rgba(0,0,0,0.08)", display: "flex", flexDirection: "column" }} onClick={e => e.stopPropagation()}>
                        
                        {/* Header & Close Button */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                            <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 700, color: "var(--text, #1c1c1e)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "70%" }}>
                                {selectedInvoice?.client_name || selectedDoc?.client_name || "Неизвестный клиент"}
                            </h2>
                            <button onClick={closeDetails} style={{ background: "var(--segment-bg, #f2f2f7)", border: "none", borderRadius: "50%", width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted, #8e8e93)", cursor: "pointer" }}>
                                <Icon name="close" style={{ fontSize: "18px" }} />
                            </button>
                        </div>

                        {/* Amount */}
                        <h1 style={{ margin: "0 0 8px 0", fontSize: "30px", fontWeight: 800, color: "var(--text, #1c1c1e)", letterSpacing: "-0.5px" }}>
                            {selectedInvoice?.total_amount !== undefined ? formatMoney(selectedInvoice.total_amount) : (selectedDoc?.total_sum || "0")} ₸
                        </h1>

                        {/* Status / Type Badge + EDO Status */}
                        <div style={{ marginBottom: "16px", display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
                            {isNonInvoiceDoc && docTypeBadge ? (
                                <span style={{ background: docTypeBadge.bg, color: docTypeBadge.color, padding: "4px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 700, display: "inline-block" }}>
                                    {docTypeBadge.code}
                                </span>
                            ) : (
                                <span style={{ background: activeColor.bg, color: activeColor.text, padding: "4px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 700, display: "inline-block" }}>
                                    {statusLabels[status]}
                                </span>
                            )}
                            {/* EDO Status Badge */}
                            {isNonInvoiceDoc && selectedDoc?.edo_status && selectedDoc.edo_status !== "draft" && (
                                <EdoStatusBadge status={selectedDoc.edo_status} style={{ padding: "4px 10px", borderRadius: "8px", fontSize: "12px" }} />
                            )}
                        </div>

                        {/* Non-invoice doc: simple info */}
                        {isNonInvoiceDoc && selectedDoc && (
                            <div style={{ paddingBottom: "16px", borderBottom: "1px solid var(--separator, #f2f2f7)", marginBottom: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px" }}>
                                    <span style={{ color: "var(--text-muted, #8e8e93)", fontWeight: 500 }}>Создан:</span>
                                    <span style={{ color: "var(--text, #1c1c1e)", fontWeight: 600 }}>{new Date(selectedDoc.created_at).toLocaleDateString("ru-RU")}</span>
                                </div>
                            </div>
                        )}

                        {/* Details list (if invoice) */}
                        {selectedInvoice && (
                            <div style={{ paddingBottom: "16px", borderBottom: "1px solid var(--separator, #f2f2f7)", marginBottom: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px" }}>
                                    <span style={{ color: "var(--text-muted, #8e8e93)", fontWeight: 500 }}>Выставлен:</span>
                                    <span style={{ color: "var(--text, #1c1c1e)", fontWeight: 600 }}>{selectedInvoice.date ? new Date(selectedInvoice.date).toLocaleDateString("ru-RU") : "—"}</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px" }}>
                                    <span style={{ color: "var(--text-muted, #8e8e93)", fontWeight: 500 }}>Срок оплаты:</span>
                                    <span style={{ color: "var(--text, #1c1c1e)", fontWeight: 600 }}>{selectedInvoice.due_date ? new Date(selectedInvoice.due_date).toLocaleDateString("ru-RU") : "—"}</span>
                                </div>
                                {isPaid && selectedInvoice.updated_at && (
                                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px" }}>
                                        <span style={{ color: "var(--ios-green, #34C759)", fontWeight: 500 }}>Оплачен:</span>
                                        <span style={{ color: "var(--text, #1c1c1e)", fontWeight: 600 }}>{new Date(selectedInvoice.updated_at).toLocaleDateString("ru-RU")}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Mark as paid toggle (Hidden if already paid) */}
                        {selectedInvoice && !isPaid && (
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                                <span style={{ fontSize: "15px", fontWeight: 600, color: "var(--text, #1c1c1e)" }}>Счет оплачен</span>
                                <Switch
                                    checked={isPaid}
                                    onChange={() => isPaid ? markInvoiceSent(selectedInvoice.id) : markInvoicePaid(selectedInvoice.id)}
                                    disabled={busy !== "idle"}
                                />
                            </div>
                        )}

                        {/* Action Buttons Row */}
                        {selectedInvoice && (
                            <div style={{ display: "flex", justifyContent: "space-around", marginBottom: "16px", padding: "0 4px" }}>
                                <IconButton icon="send" label="Отправить" onClick={sendInvoice} busy={busy === "send"} />
                                <IconButton icon="notifications" label="Напомнить" onClick={() => selectedInvoice && sendReminder(selectedInvoice.id)} disabled={!selectedInvoice || status === "paid"} busy={busy === "remind"} />
                                <IconButton icon="post_add" label="Создать" onClick={() => setShowDocMenu(true)} disabled={!isPaid} />
                            </div>
                        )}

                        {/* ЭЦП Sign Button (Only for docs not yet signed by both / not rejected) */}
                        {selectedDoc && (!selectedDoc.edo_status || !['signed_both', 'rejected', 'completed', 'esf_submitted', 'esf_pending'].includes(selectedDoc.edo_status)) && (
                            <button
                                onClick={() => { closeDetails(); setTimeout(() => setShowSignSheet(true), 350); }}
                                style={{
                                    width: "100%", height: "48px", border: "none", borderRadius: "14px",
                                    background: "linear-gradient(135deg, #007AFF, #5856D6)",
                                    color: "#fff", fontSize: "15px", fontWeight: 600,
                                    cursor: "pointer", display: "flex", alignItems: "center",
                                    justifyContent: "center", gap: "8px",
                                    boxShadow: "0 4px 16px rgba(0, 122, 255, 0.25)",
                                    marginBottom: "8px",
                                }}
                            >
                                <Icon name="verified" style={{ fontSize: "20px" }} />
                                {selectedDoc.edo_status === 'signed_self' ? 'Подписано — ожидает контрагента' : 'Подписать ЭЦП'}
                            </button>
                        )}

                        {/* Signed Both — Success message */}
                        {selectedDoc?.edo_status === 'signed_both' && (
                            <div style={{
                                background: "rgba(52, 199, 89, 0.08)", borderRadius: "14px",
                                padding: "14px 16px", marginBottom: "8px",
                                display: "flex", alignItems: "center", gap: "10px",
                                border: "1px solid rgba(52, 199, 89, 0.2)",
                            }}>
                                <Icon name="verified_user" style={{ fontSize: "24px", color: "#34C759" }} />
                                <div>
                                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#34C759" }}>Документ подписан обеими сторонами</div>
                                    <div style={{ fontSize: "12px", color: "var(--text-muted, #8e8e93)", marginTop: "2px" }}>ЭЦП сформирована, PDF обновлён со штампом</div>
                                </div>
                            </div>
                        )}

                        {/* Rejected — Warning */}
                        {selectedDoc?.edo_status === 'rejected' && (
                            <div style={{
                                background: "rgba(255, 59, 48, 0.08)", borderRadius: "14px",
                                padding: "14px 16px", marginBottom: "8px",
                                display: "flex", alignItems: "center", gap: "10px",
                                border: "1px solid rgba(255, 59, 48, 0.2)",
                            }}>
                                <Icon name="cancel" style={{ fontSize: "24px", color: "#FF3B30" }} />
                                <div>
                                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#FF3B30" }}>Документ отклонён контрагентом</div>
                                    <div style={{ fontSize: "12px", color: "var(--text-muted, #8e8e93)", marginTop: "2px" }}>Вы можете создать новый документ</div>
                                </div>
                            </div>
                        )}

                        {/* Share Button (show after sender has signed) */}
                        {selectedDoc && selectedDoc.edo_status && ['signed_self', 'sent', 'signed_both'].includes(selectedDoc.edo_status) && (
                            <button
                                onClick={async () => {
                                    if (shareUrl) {
                                        try {
                                            await navigator.clipboard.writeText(window.location.origin.replace('doc.onlink.kz', 'api.doc.onlink.kz') + shareUrl);
                                            alert('Ссылка скопирована!');
                                        } catch {
                                            prompt('Скопируйте ссылку:', window.location.origin + shareUrl);
                                        }
                                        return;
                                    }
                                    setIsSharing(true);
                                    try {
                                        const result = await request<ShareInfo>('/edo/share', {
                                            method: 'POST',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({ document_id: selectedDoc.id, share_type: 'link' }),
                                        });
                                        const fullUrl = window.location.origin.replace('doc.onlink.kz', 'api.doc.onlink.kz') + '/edo/doc/' + result.share_uuid;
                                        setShareUrl('/edo/doc/' + result.share_uuid);
                                        try {
                                            await navigator.clipboard.writeText(fullUrl);
                                            alert('Ссылка скопирована!\n' + fullUrl);
                                        } catch {
                                            prompt('Скопируйте ссылку:', fullUrl);
                                        }
                                    } catch (err: any) {
                                        alert('Ошибка: ' + (err.message || 'Не удалось создать ссылку'));
                                    } finally {
                                        setIsSharing(false);
                                    }
                                }}
                                disabled={isSharing}
                                style={{
                                    width: "100%", height: "44px", border: "none", borderRadius: "14px",
                                    background: "var(--segment-bg, #f2f2f7)",
                                    color: "var(--primary, #007AFF)", fontSize: "14px", fontWeight: 600,
                                    cursor: "pointer", display: "flex", alignItems: "center",
                                    justifyContent: "center", gap: "8px",
                                }}
                            >
                                {isSharing ? (
                                    <div className="spinner" style={{ borderColor: "var(--primary, #007AFF)", borderTopColor: "transparent" }} />
                                ) : (
                                    <Icon name={shareUrl ? "content_copy" : "share"} style={{ fontSize: "18px" }} />
                                )}
                                {shareUrl ? 'Скопировать ссылку' : 'Поделиться с контрагентом'}
                            </button>
                        )}

                        {/* Signature List */}
                        {isNonInvoiceDoc && selectedDoc && (isLoadingSignatures || signatures.length > 0) && (
                            <div style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid var(--separator, #f2f2f7)" }}>
                                <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text, #1c1c1e)", marginBottom: "12px", paddingTop: "12px" }}>
                                    Подписи ЭЦП
                                </div>
                                {isLoadingSignatures ? (
                                    <div style={{ display: "flex", justifyContent: "center", padding: "10px" }}>
                                        <div className="spinner" style={{ width: "24px", height: "24px", borderColor: "var(--primary, #007AFF)", borderTopColor: "transparent", borderWidth: "2px" }} />
                                    </div>
                                ) : (
                                    <SignatureList signatures={signatures} />
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Action Sheet Modal for "Создать на основании" (Stays on top of Details Modal) */}
            {(showDocMenu || isClosingDocMenu) && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1100, display: "flex", alignItems: "flex-end", backdropFilter: "blur(2px)", opacity: isClosingDocMenu ? 0 : 1, transition: "opacity 0.3s ease" }} onClick={closeDocMenu}>
                    <div className={isClosingDocMenu ? "animate-slide-down" : "animate-slide-up"} style={{ width: "100%", background: "var(--card, #fff)", borderTopLeftRadius: "24px", borderTopRightRadius: "24px", padding: "12px 20px 32px", paddingBottom: "max(32px, env(safe-area-inset-bottom))" }} onClick={e => e.stopPropagation()}>
                        {/* Grabber */}
                        <div style={{ width: "36px", height: "5px", borderRadius: "3px", backgroundColor: "var(--separator, #C7C7CC)", margin: "0 auto 16px" }} />
                        
                        <h3 style={{ margin: "0 0 20px 0", fontSize: "20px", fontWeight: 700, color: "var(--text, #1c1c1e)", textAlign: "left" }}>Создать на основании</h3>
                        
                        <div style={{ display: "flex", flexDirection: "column" }}>
                            <button
                                onClick={() => {
                                    closeDocMenu();
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "act");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "56px", background: "none", border: "none", color: "var(--text, #1c1c1e)", fontSize: "17px", fontWeight: 500, display: "flex", alignItems: "center", gap: "16px", padding: "0", cursor: "pointer", width: "100%", opacity: busy === "generate" ? 0.6 : 1 }}
                            >
                                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "rgba(0, 122, 255, 0.1)", color: "var(--primary, #007AFF)", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="description" style={{ fontSize: "20px" }} /></div>
                                <span>Акт выполненных работ (АВР)</span>
                            </button>
                            <button
                                onClick={() => {
                                    closeDocMenu();
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "waybill");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "56px", background: "none", border: "none", color: "var(--text, #1c1c1e)", fontSize: "17px", fontWeight: 500, display: "flex", alignItems: "center", gap: "16px", padding: "0", cursor: "pointer", width: "100%", opacity: busy === "generate" ? 0.6 : 1 }}
                            >
                                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "rgba(0, 122, 255, 0.1)", color: "var(--primary, #007AFF)", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="description" style={{ fontSize: "20px" }} /></div>
                                <span>Накладная на отпуск запасов</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Context Actions Menu (Popover Style like Telegram) */}
            {(showActionsMenu || isClosingActions) && (
                <div 
                    style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 1200, pointerEvents: "auto" }} 
                    onClick={closeActionsMenu}
                >
                    <div 
                        className={isClosingActions ? "animate-ios-popover-out" : "animate-ios-popover"}
                        style={{ 
                            position: "absolute", 
                            top: "60px", 
                            right: "16px", 
                            width: "190px", 
                            background: "rgba(28, 28, 30, 0.9)", 
                            backdropFilter: "blur(20px)",
                            borderRadius: "14px", 
                            padding: "6px 0", 
                            boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
                            display: "flex", 
                            flexDirection: "column",
                            color: "#fff",
                            overflow: "hidden",
                            transformOrigin: "top right",
                            zIndex: 1201
                        }} 
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Mark As Sent Action (invoices only) */}
                        {selectedInvoice && status === "draft" && (
                            <button
                                onClick={() => {
                                    closeActionsMenu();
                                    markInvoiceSent(selectedInvoice.id);
                                }}
                                disabled={busy !== "idle"}
                                className="popover-item"
                                style={{ 
                                    height: "44px", 
                                    background: "none", 
                                    border: "none", 
                                    color: "#fff", 
                                    fontSize: "16px", 
                                    fontWeight: 500, 
                                    display: "flex", 
                                    alignItems: "center", 
                                    gap: "12px", 
                                    padding: "0 16px", 
                                    cursor: "pointer", 
                                    width: "100%",
                                    borderBottom: "0.5px solid rgba(255,255,255,0.1)"
                                }}
                            >
                                <Icon name="mark_email_read" style={{ fontSize: "20px" }} />
                                <span>Отправить (вручную)</span>
                            </button>
                        )}

                        {/* Edit Action (invoices only, hidden for AVR/Waybill) */}
                        {selectedInvoice && (
                            <button
                                onClick={() => {
                                    closeActionsMenu();
                                    setSubView("invoiceForm");
                                }}
                                className="popover-item"
                                style={{ 
                                    height: "44px", 
                                    background: "none", 
                                    border: "none", 
                                    color: "#fff", 
                                    fontSize: "16px", 
                                    fontWeight: 500, 
                                    display: "flex", 
                                    alignItems: "center", 
                                    gap: "12px", 
                                    padding: "0 16px", 
                                    cursor: "pointer", 
                                    width: "100%",
                                    borderBottom: "0.5px solid rgba(255,255,255,0.1)"
                                }}
                            >
                                <Icon name="edit" style={{ fontSize: "20px" }} />
                                <span>Изменить</span>
                            </button>
                        )}
                        
                        {/* Delete Action */}
                        <button
                            onClick={() => {
                                closeActionsMenu();
                                deleteInvoice();
                            }}
                            disabled={busy !== "idle"}
                            className="popover-item"
                            style={{ 
                                height: "44px", 
                                background: "none", 
                                border: "none", 
                                color: "#FF453A", 
                                fontSize: "16px", 
                                fontWeight: 500, 
                                display: "flex", 
                                alignItems: "center", 
                                gap: "12px", 
                                padding: "0 16px", 
                                cursor: "pointer", 
                                width: "100%"
                            }}
                        >
                            <Icon name="delete" style={{ fontSize: "20px" }} />
                            <span>Удалить</span>
                        </button>
                    </div>
                </div>
            )}

            {/* EDO Signing Sheet */}
            {showSignSheet && (
                <SignDocumentSheet
                    documentId={(selectedInvoice as any)?.id || selectedDoc?.id || 0}
                    documentTitle={title}
                    signerRole={(selectedDoc as any)?.is_incoming ? "receiver" : "sender"}
                    onClose={() => setShowSignSheet(false)}
                    onSigned={() => {
                        setShowSignSheet(false);
                        // Refresh the preview in-place with the stamped PDF
                        const docId = (selectedInvoice as any)?.id || selectedDoc?.id;
                        if (docId && refreshPreview) {
                            refreshPreview(docId);
                        }
                        if (reloadDocuments) {
                            reloadDocuments();
                        }
                    }}
                />
            )}
        </div>
    );
}
