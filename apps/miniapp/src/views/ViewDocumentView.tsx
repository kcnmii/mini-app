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
    busy: string;
    animationType?: "none" | "left" | "up";
}

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
    busy,
    animationType = "left"
}: ViewDocumentViewProps) {
    const [showDocMenu, setShowDocMenu] = useState(false);
    const animClass = animationType === "none" ? "" : animationType === "up" ? "animate-slide-up" : "animate-slide-left";
    const statusLabels: Record<string, string> = { draft: "Черновик", sent: "Отправлен", paid: "Оплачен", overdue: "Просрочен" };
    const statusColors: Record<string, string> = { draft: "#8E8E93", sent: "#FF9500", paid: "#34C759", overdue: "#FF3B30" };

    return (
        <>
            <div className={`nav-bar ${animClass}`}>
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
                        <Icon name="chevron_left" className="large-icon" />
                    </button>
                    <span className="nav-bar-title-center">
                        {selectedInvoice?.number || selectedDoc?.title.replace(/^Счет\s*(№|N)?\s*/i, "") || "Просмотр"}
                    </span>
                    <div className="nav-bar-right">
                        <button className="nav-bar-btn-circle" onClick={() => setSubView("invoiceForm")}>
                            <Icon name="edit" />
                        </button>
                    </div>
                </div>
            </div>

            <div className={`content-area ${animClass}`} style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px)", overflow: "hidden", paddingBottom: 0 }}>
                {/* Compact Info Bar — Forced Light Theme for contrast */}
                {selectedInvoice && (
                    <div style={{ padding: "10px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--card)", borderBottom: "1px solid var(--separator)", flexShrink: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <span style={{ display: "inline-block", padding: "3px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, color: "#fff", background: statusColors[selectedInvoice.status] || "#8E8E93", textTransform: "uppercase" }}>
                                {statusLabels[selectedInvoice.status] || selectedInvoice.status}
                            </span>
                            <span style={{ fontSize: "15px", fontWeight: 700, color: "var(--text)" }}>{formatMoney(selectedInvoice.total_amount)} ₸</span>
                        </div>
                        <span style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500, maxWidth: "50%", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{selectedInvoice.client_name}</span>
                    </div>
                )}

                {/* Document preview — images with pinch-to-zoom */}
                <div style={{
                    flex: 1,
                    overflow: "auto",
                    WebkitOverflowScrolling: "touch",
                    touchAction: "pan-x pan-y pinch-zoom",
                    backgroundColor: "#e5e5ea",
                    position: "relative"
                }}>
                    {isPdfLoading && previewPages.length === 0 && (
                        <div style={{
                            position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
                            display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center",
                            backgroundColor: "rgba(255,255,255,0.9)", zIndex: 10
                        }}>
                            <div style={{ width: "32px", height: "32px", border: "3px solid #007AFF", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                        </div>

                    )}

                    {previewPages.length > 0 ? (
                        <div style={{ padding: "8px", paddingBottom: "160px" }}>
                            {previewPages.map((src, i) => (
                                <img
                                    key={i}
                                    src={src}
                                    alt={`Страница ${i + 1}`}
                                    style={{
                                        width: "100%",
                                        display: "block",
                                        borderRadius: "4px",
                                        marginBottom: i < previewPages.length - 1 ? "8px" : "0",
                                        boxShadow: "0 1px 4px rgba(0,0,0,0.15)"
                                    }}
                                />
                            ))}
                        </div>
                    ) : !isPdfLoading && (
                        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%", color: "var(--text-secondary)", fontSize: "14px" }}>
                            Нет превью
                        </div>
                    )}
                </div>
            </div>

            {/* Bottom Action Bar — Styled like Invoice Footer */}
            <div className={`invoice-footer ${animClass}`} style={{ background: "var(--card)", borderTop: "1px solid var(--separator)" }}>

                <div className="invoice-footer-inner">
                    <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
                        {(selectedInvoice && (selectedInvoice.status as string) !== "paid") && (
                            <>
                                <button
                                    onClick={() => markInvoicePaid(selectedInvoice!.id)}
                                    style={{ flex: 1, height: "48px", borderRadius: "12px", border: "none", background: "#34C759", color: "#fff", fontSize: "15px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
                                >
                                    <Icon name="check_circle" /> Оплачен
                                </button>

                                <button
                                    onClick={() => sendReminder(selectedInvoice!.id)}
                                    disabled={busy === "remind"}
                                    style={{ flex: 1, height: "48px", borderRadius: "12px", border: "none", background: "#007AFF", color: "#fff", fontSize: "15px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", opacity: busy === "remind" ? 0.6 : 1 }}
                                >
                                    <Icon name="notifications" /> {busy === "remind" ? "Отправка..." : "Напомнить"}
                                </button>

                                {selectedInvoice.status === "draft" && (
                                    <button
                                        onClick={() => markInvoiceSent(selectedInvoice!.id)}
                                        style={{ flex: 1, height: "48px", borderRadius: "12px", border: "none", background: "#FF9500", color: "#fff", fontSize: "15px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
                                    >
                                        <Icon name="send" /> Отправлен
                                    </button>
                                )}
                            </>
                        )}

                        {(selectedInvoice && selectedInvoice.status === "paid") && (
                            <button
                                onClick={() => setShowDocMenu(true)}
                                style={{ flex: 1, height: "48px", borderRadius: "12px", border: "none", background: "#5856D6", color: "#fff", fontSize: "15px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
                            >
                                <Icon name="post_add" /> Создать на основании
                            </button>
                        )}
                    </div>

                    <button className="invoice-send-btn" onClick={sendInvoice} disabled={busy !== "idle"}>
                        <Icon name="send" />{busy === "send" ? "Отправка..." : "Отправить"}
                    </button>
                </div>
            </div>

            {/* Action Sheet Modal for "Создать на основании" */}
            {showDocMenu && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.4)", zIndex: 1000, display: "flex", alignItems: "flex-end" }} onClick={() => setShowDocMenu(false)}>
                    <div style={{ width: "100%", background: "var(--bg)", borderTopLeftRadius: "16px", borderTopRightRadius: "16px", padding: "16px", paddingBottom: "max(16px, env(safe-area-inset-bottom))", animation: "slide-up 0.3s ease-out" }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                            <h3 style={{ margin: 0, fontSize: "18px", color: "var(--text)" }}>Создать документ</h3>
                            <button onClick={() => setShowDocMenu(false)} style={{ background: "transparent", border: "none", color: "var(--text-secondary)", cursor: "pointer" }}><Icon name="close" /></button>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                            <button
                                onClick={() => {
                                    setShowDocMenu(false);
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "act");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "56px", borderRadius: "12px", border: "none", background: "var(--card)", color: "var(--text)", fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "12px", padding: "0 16px", cursor: "pointer", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}
                            >
                                <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "rgba(0, 122, 255, 0.1)", color: "#007AFF", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="assignment" /></div>
                                Акт выполненных работ (АВР)
                            </button>
                            <button
                                onClick={() => {
                                    setShowDocMenu(false);
                                    if (selectedInvoice) generateDocument(selectedInvoice.id, "waybill");
                                }}
                                disabled={busy === "generate"}
                                style={{ height: "56px", borderRadius: "12px", border: "none", background: "var(--card)", color: "var(--text)", fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "12px", padding: "0 16px", cursor: "pointer", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}
                            >
                                <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "rgba(52, 199, 89, 0.1)", color: "#34C759", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="local_shipping" /></div>
                                Накладная на отпуск запасов
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
