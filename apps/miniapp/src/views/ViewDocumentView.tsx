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
    animationType = "left"
}: ViewDocumentViewProps) {
    const [showDocMenu, setShowDocMenu] = useState(false);
    const [showActionsMenu, setShowActionsMenu] = useState(false);
    const [showDetails, setShowDetails] = useState(false);
    const [isClosingDetails, setIsClosingDetails] = useState(false);
    const [isClosingDocMenu, setIsClosingDocMenu] = useState(false);
    const [isClosingActions, setIsClosingActions] = useState(false);

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
        }, 300);
    };

    const animClass = animationType === "none" ? "" : animationType === "up" ? "animate-slide-up" : "animate-slide-left";

    const title = selectedInvoice?.number ? `# ${selectedInvoice.number}` : (selectedDoc?.title || "");
    const status = selectedInvoice?.status || "document";
    const statusLabels: Record<string, string> = { draft: "Черновик", sent: "Отправлен", paid: "Оплачен", overdue: "Просрочен", document: "Архив" };
    const statusColors: Record<string, { bg: string, text: string }> = {
        draft: { bg: "var(--segment-bg, #f2f2f7)", text: "var(--text-muted, #8E8E93)" },
        sent: { bg: "#FFF4E5", text: "#FF9500" },
        paid: { bg: "#E8F8EE", text: "#34C759" },
        overdue: { bg: "#FFECEB", text: "#FF3B30" },
        document: { bg: "var(--separator, #E2E2E6)", text: "var(--text, #48484A)" }
    };
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
                    onClick={() => setShowDetails(true)} 
                    style={{ pointerEvents: "auto", background: "var(--primary, #007AFF)", color: "#ffffff", height: "40px", padding: "0 20px", borderRadius: "20px", border: "none", fontSize: "14px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px", boxShadow: "0 4px 16px rgba(0, 122, 255, 0.3)", cursor: "pointer" }}
                >
                    Подробнее
                    <Icon name="keyboard_arrow_up" style={{ fontSize: "18px", opacity: 0.9 }} />
                </button>
            </div>

            {/* Details Modal */}
            {(showDetails || isClosingDetails) && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.6)", zIndex: 900, display: "flex", alignItems: "flex-end", backdropFilter: "blur(4px)", opacity: isClosingDetails ? 0 : 1, transition: "opacity 0.3s ease" }} onClick={closeDetails}>
                    <div className={isClosingDetails ? "animate-slide-down" : "animate-slide-up"} style={{ width: "100%", background: "var(--bg, #ffffff)", borderTopLeftRadius: "24px", borderTopRightRadius: "24px", padding: "16px 20px", paddingBottom: "max(24px, env(safe-area-inset-bottom))", boxShadow: "0 -8px 40px rgba(0,0,0,0.08)", display: "flex", flexDirection: "column" }} onClick={e => e.stopPropagation()}>
                        
                        {/* Header & Close Button */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                            <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 700, color: "var(--text, #1c1c1e)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "70%" }}>
                                {selectedInvoice?.client_name || selectedDoc?.client_name || "Неизвестный клиент"}
                            </h2>
                            <button onClick={closeDetails} style={{ background: "var(--segment-bg, #f2f2f7)", border: "none", borderRadius: "50%", width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted, #8e8e93)", cursor: "pointer" }}>
                                <Icon name="close" style={{ fontSize: "18px" }} />
                            </button>
                        </div>

                        {/* Status Badge */}
                        <div style={{ marginBottom: "12px" }}>
                            <span style={{ background: activeColor.bg, color: activeColor.text, padding: "4px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 700, display: "inline-block" }}>
                                {statusLabels[status]}
                            </span>
                        </div>

                        {/* Amount */}
                        <h1 style={{ margin: "0 0 16px 0", fontSize: "30px", fontWeight: 800, color: "var(--text, #1c1c1e)", letterSpacing: "-0.5px" }}>
                            {selectedInvoice?.total_amount !== undefined ? formatMoney(selectedInvoice.total_amount) : (selectedDoc?.total_sum || "0")} ₸
                        </h1>

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
                            </div>
                        )}

                        {/* Mark as paid toggle */}
                        {selectedInvoice && (
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
                        <div style={{ display: "flex", justifyContent: "space-around", marginBottom: "16px", padding: "0 4px" }}>
                            <IconButton icon="send" label="Отправить" onClick={sendInvoice} busy={busy === "send"} />
                            <IconButton icon="notifications" label="Напомнить" onClick={() => selectedInvoice && sendReminder(selectedInvoice.id)} disabled={!selectedInvoice || status === "paid"} busy={busy === "remind"} />
                            <IconButton icon="post_add" label="Документ" onClick={() => setShowDocMenu(true)} disabled={!isPaid} />
                        </div>
                    </div>
                </div>
            )}

            {/* Action Sheet Modal for "Создать на основании" (Stays on top of Details Modal) */}
            {(showDocMenu || isClosingDocMenu) && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1100, display: "flex", alignItems: "flex-end", backdropFilter: "blur(2px)", opacity: isClosingDocMenu ? 0 : 1, transition: "opacity 0.3s ease" }} onClick={closeDocMenu}>
                    <div className={isClosingDocMenu ? "animate-slide-down" : "animate-slide-up"} style={{ width: "100%", background: "var(--bg, #fff)", borderTopLeftRadius: "24px", borderTopRightRadius: "24px", padding: "24px", paddingBottom: "max(24px, env(safe-area-inset-bottom))" }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
                            <h3 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "var(--text, #1c1c1e)" }}>Создать документ</h3>
                            <button onClick={closeDocMenu} style={{ background: "var(--segment-bg, #f2f2f7)", border: "none", borderRadius: "50%", width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted, #8e8e93)", cursor: "pointer" }}><Icon name="close" /></button>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                            <button
                                onClick={() => {
                                    closeDocMenu();
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "act");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "64px", borderRadius: "16px", border: "1px solid var(--border, rgba(0,0,0,0.05))", background: "var(--card, #fff)", color: "var(--text, #1c1c1e)", fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "16px", padding: "0 20px", cursor: "pointer", boxShadow: "0 2px 10px rgba(0,0,0,0.02)" }}
                            >
                                <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(0, 122, 255, 0.1)", color: "var(--primary, #007AFF)", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="assignment" /></div>
                                Акт выполненных работ (АВР)
                            </button>
                            <button
                                onClick={() => {
                                    closeDocMenu();
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "waybill");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "64px", borderRadius: "16px", border: "1px solid var(--border, rgba(0,0,0,0.05))", background: "var(--card, #fff)", color: "var(--text, #1c1c1e)", fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "16px", padding: "0 20px", cursor: "pointer", boxShadow: "0 2px 10px rgba(0,0,0,0.02)" }}
                            >
                                <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(52, 199, 89, 0.1)", color: "#34C759", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="local_shipping" /></div>
                                Накладная на отпуск запасов
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
                            width: "220px", 
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
                        {/* Edit Action */}
                        <button
                            onClick={() => {
                                closeActionsMenu();
                                if (selectedInvoice) setSubView("invoiceForm");
                            }}
                            disabled={!selectedInvoice}
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
                                borderBottom: "0.5px solid rgba(255,255,255,0.1)",
                                opacity: !selectedInvoice ? 0.5 : 1
                            }}
                        >
                            <Icon name="edit" style={{ fontSize: "20px" }} />
                            <span>Изменить счет</span>
                        </button>
                        
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
        </div>
    );
}
