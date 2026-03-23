import React, { useState } from "react";
import { Icon } from "../components/Common";
import { formatMoney } from "../utils";
import type { InvoiceRecord, DocumentRecord } from "../types";

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
}

const IconButton = ({ icon, label, onClick, disabled, busy }: any) => (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px", opacity: disabled ? 0.3 : 1, pointerEvents: disabled ? "none" : "auto", cursor: "pointer", transition: "0.2s" }} onClick={onClick}>
        <div style={{ width: "52px", height: "52px", borderRadius: "18px", background: "#f8f8fb", display: "flex", justifyContent: "center", alignItems: "center", color: "#1c1c1e", border: "1px solid rgba(0,0,0,0.03)" }}>
            {busy ? <div className="spinner" style={{ borderColor: "#1c1c1e", borderTopColor: "transparent" }} /> : <Icon name={icon} style={{ fontSize: "24px" }} />}
        </div>
        <span style={{ fontSize: "12px", fontWeight: 600, color: "#1c1c1e" }}>{label}</span>
    </div>
);

const Switch = ({ checked, onChange, disabled }: any) => {
    return (
        <div
            onClick={(e) => { e.stopPropagation(); if (!disabled) onChange(!checked); }}
            style={{ width: "50px", height: "30px", borderRadius: "15px", background: checked ? "#34C759" : "#e5e5ea", position: "relative", cursor: "pointer", transition: "0.3s", opacity: disabled ? 0.6 : 1 }}
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
    animationType = "left"
}: ViewDocumentViewProps) {
    const [showDocMenu, setShowDocMenu] = useState(false);
    const [showDetails, setShowDetails] = useState(false);
    const animClass = animationType === "none" ? "" : animationType === "up" ? "animate-slide-up" : "animate-slide-left";

    const title = selectedInvoice?.number ? `# ${selectedInvoice.number}` : (selectedDoc?.title || "");
    const status = selectedInvoice?.status || "document";
    const statusLabels: Record<string, string> = { draft: "Черновик", sent: "Отправлен", paid: "Оплачен", overdue: "Просрочен", document: "Архив" };
    const statusColors: Record<string, { bg: string, text: string }> = {
        draft: { bg: "#f2f2f7", text: "#8E8E93" },
        sent: { bg: "#FFF4E5", text: "#FF9500" },
        paid: { bg: "#E8F8EE", text: "#34C759" },
        overdue: { bg: "#FFECEB", text: "#FF3B30" },
        document: { bg: "#E2E2E6", text: "#48484A" }
    };
    const activeColor = statusColors[status] || statusColors.draft;

    const isPaid = status === "paid";

    return (
        <div className={`content-area ${animClass}`} style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", background: "#e5e5ea", zIndex: 50, display: "flex", flexDirection: "column" }}>
            {/* Top Bar */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px", paddingTop: "max(16px, env(safe-area-inset-top))", flexShrink: 0, background: "#f2f2f7" }}>
                <span style={{ fontWeight: 700, fontSize: "20px", color: "#1c1c1e", letterSpacing: "-0.5px" }}>{title}</span>
                <button onClick={() => setSubView(null)} style={{ background: "#e5e5ea", border: "none", borderRadius: "50%", width: "36px", height: "36px", display: "flex", alignItems: "center", justifyContent: "center", color: "#8e8e93", cursor: "pointer" }}>
                    <Icon name="close" />
                </button>
            </div>

            {/* Document Pages Container */}
            <div style={{ flex: 1, overflow: "auto", WebkitOverflowScrolling: "touch", padding: "16px", paddingBottom: "120px", touchAction: "pan-x pan-y pinch-zoom" }}>
                {isPdfLoading && previewPages.length === 0 ? (
                    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
                        <div className="spinner" style={{ width: "40px", height: "40px", borderColor: "#007AFF", borderTopColor: "transparent" }} />
                    </div>
                ) : previewPages.length > 0 ? (
                    previewPages.map((src, i) => (
                        <img key={i} src={src} alt={`Page ${i + 1}`} style={{ width: "100%", borderRadius: "8px", boxShadow: "0 2px 10px rgba(0,0,0,0.1)", marginBottom: "16px", display: "block" }} />
                    ))
                ) : (
                    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%", color: "#8e8e93", fontWeight: 500 }}>
                        Нет превью
                    </div>
                )}
            </div>

            {/* Floating 'Подробнее' Button */}
            {!showDetails && (
                <div style={{ position: "fixed", bottom: "max(32px, env(safe-area-inset-bottom))", left: "0", right: "0", display: "flex", justifyContent: "center", zIndex: 60, pointerEvents: "none" }}>
                    <button 
                        onClick={() => setShowDetails(true)} 
                        style={{ pointerEvents: "auto", background: "rgba(28, 28, 30, 0.85)", backdropFilter: "blur(12px)", color: "#fff", height: "56px", padding: "0 32px", borderRadius: "28px", border: "none", fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "10px", boxShadow: "0 8px 32px rgba(0,0,0,0.15)", cursor: "pointer" }}
                    >
                        Подробнее
                        <Icon name="keyboard_arrow_up" style={{ fontSize: "20px", opacity: 0.8 }} />
                    </button>
                </div>
            )}

            {/* Details Modal */}
            {showDetails && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 900, display: "flex", alignItems: "flex-end", backdropFilter: "blur(4px)" }} onClick={() => setShowDetails(false)}>
                    <div style={{ width: "100%", background: "#ffffff", borderTopLeftRadius: "32px", borderTopRightRadius: "32px", padding: "20px 24px 32px 24px", paddingBottom: "max(32px, env(safe-area-inset-bottom))", boxShadow: "0 -8px 40px rgba(0,0,0,0.08)", display: "flex", flexDirection: "column", animation: "slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1)" }} onClick={e => e.stopPropagation()}>
                        
                        {/* Header & Close Button */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                            <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#1c1c1e", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "70%" }}>
                                {selectedInvoice?.client_name || selectedDoc?.client_name || "Неизвестный клиент"}
                            </h2>
                            <button onClick={() => setShowDetails(false)} style={{ background: "#f2f2f7", border: "none", borderRadius: "50%", width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", color: "#8e8e93", cursor: "pointer" }}>
                                <Icon name="close" style={{ fontSize: "18px" }} />
                            </button>
                        </div>

                        {/* Status Badge */}
                        <div style={{ marginBottom: "16px" }}>
                            <span style={{ background: activeColor.bg, color: activeColor.text, padding: "6px 12px", borderRadius: "10px", fontSize: "13px", fontWeight: 700, display: "inline-block" }}>
                                {statusLabels[status]}
                            </span>
                        </div>

                        {/* Amount */}
                        <h1 style={{ margin: "0 0 24px 0", fontSize: "34px", fontWeight: 800, color: "#1c1c1e", letterSpacing: "-0.5px" }}>
                            {selectedInvoice?.total_amount !== undefined ? formatMoney(selectedInvoice.total_amount) : (selectedDoc?.total_sum || "0")} ₸
                        </h1>

                        {/* Details list (if invoice) */}
                        {selectedInvoice && (
                            <div style={{ paddingBottom: "20px", borderBottom: "1px solid #f2f2f7", marginBottom: "20px", display: "flex", flexDirection: "column", gap: "10px" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "15px" }}>
                                    <span style={{ color: "#8e8e93", fontWeight: 500 }}>Выставлен:</span>
                                    <span style={{ color: "#1c1c1e", fontWeight: 600 }}>{selectedInvoice.date ? new Date(selectedInvoice.date).toLocaleDateString("ru-RU") : "—"}</span>
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "15px" }}>
                                    <span style={{ color: "#8e8e93", fontWeight: 500 }}>Срок оплаты:</span>
                                    <span style={{ color: "#1c1c1e", fontWeight: 600 }}>{selectedInvoice.due_date ? new Date(selectedInvoice.due_date).toLocaleDateString("ru-RU") : "—"}</span>
                                </div>
                            </div>
                        )}

                        {/* Mark as paid toggle */}
                        {selectedInvoice && (
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
                                <span style={{ fontSize: "16px", fontWeight: 600, color: "#1c1c1e" }}>Счет оплачен</span>
                                <Switch
                                    checked={isPaid}
                                    onChange={() => isPaid ? markInvoiceSent(selectedInvoice.id) : markInvoicePaid(selectedInvoice.id)}
                                    disabled={busy !== "idle"}
                                />
                            </div>
                        )}

                        {/* Action Buttons Row */}
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "32px", padding: "0 8px" }}>
                            <IconButton icon="edit" label="Изменить" onClick={() => { if (selectedInvoice) setSubView("invoiceForm"); setShowDetails(false); }} disabled={!selectedInvoice} />
                            <IconButton icon="send" label="Отправить" onClick={sendInvoice} busy={busy === "send"} />
                            <IconButton icon="notifications" label="Напомнить" onClick={() => selectedInvoice && sendReminder(selectedInvoice.id)} disabled={!selectedInvoice || status === "paid"} busy={busy === "remind"} />
                            <IconButton icon="post_add" label="Документ" onClick={() => setShowDocMenu(true)} disabled={!isPaid} />
                        </div>

                        {/* Delete Button */}
                        <button
                            onClick={() => deleteInvoice()}
                            disabled={busy !== "idle"}
                            style={{ width: "100%", height: "56px", borderRadius: "18px", background: "#fff5f5", color: "#FF3B30", border: "none", fontSize: "16px", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", cursor: "pointer", opacity: busy !== "idle" ? 0.6 : 1 }}
                        >
                            <Icon name="delete" /> Удалить
                        </button>
                    </div>
                </div>
            )}

            {/* Action Sheet Modal for "Создать на основании" (Stays on top of Details Modal) */}
            {showDocMenu && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "flex-end", backdropFilter: "blur(2px)" }} onClick={() => setShowDocMenu(false)}>
                    <div style={{ width: "100%", background: "#fff", borderTopLeftRadius: "24px", borderTopRightRadius: "24px", padding: "24px", paddingBottom: "max(24px, env(safe-area-inset-bottom))", animation: "slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1)" }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
                            <h3 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#1c1c1e" }}>Создать документ</h3>
                            <button onClick={() => setShowDocMenu(false)} style={{ background: "#f2f2f7", border: "none", borderRadius: "50%", width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", color: "#8e8e93", cursor: "pointer" }}><Icon name="close" /></button>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                            <button
                                onClick={() => {
                                    setShowDocMenu(false);
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "act");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "64px", borderRadius: "16px", border: "1px solid rgba(0,0,0,0.05)", background: "#fff", color: "#1c1c1e", fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "16px", padding: "0 20px", cursor: "pointer", boxShadow: "0 2px 10px rgba(0,0,0,0.02)" }}
                            >
                                <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(0, 122, 255, 0.1)", color: "#007AFF", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="assignment" /></div>
                                Акт выполненных работ (АВР)
                            </button>
                            <button
                                onClick={() => {
                                    setShowDocMenu(false);
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "waybill");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "64px", borderRadius: "16px", border: "1px solid rgba(0,0,0,0.05)", background: "#fff", color: "#1c1c1e", fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "16px", padding: "0 20px", cursor: "pointer", boxShadow: "0 2px 10px rgba(0,0,0,0.02)" }}
                            >
                                <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(52, 199, 89, 0.1)", color: "#34C759", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="local_shipping" /></div>
                                Накладная на отпуск запасов
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
