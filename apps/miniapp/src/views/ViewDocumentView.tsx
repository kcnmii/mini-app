import React from "react";
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
}

export function ViewDocumentView({
    setSubView,
    selectedInvoice,
    selectedDoc,
    isPdfLoading,
    previewPages,
    markInvoicePaid,
    markInvoiceSent
}: ViewDocumentViewProps) {
    const statusLabels: Record<string, string> = { draft: "Черновик", sent: "Отправлен", paid: "Оплачен", overdue: "Просрочен" };
    const statusColors: Record<string, string> = { draft: "#8E8E93", sent: "#FF9500", paid: "#34C759", overdue: "#FF3B30" };

    return (
        <>
            <header className="nav-bar" style={{ background: "#fff", borderBottom: "1px solid #e5e5ea" }}>
                <div className="nav-bar-detail" style={{ background: "#fff" }}>
                    <button className="nav-bar-btn-circle" onClick={() => setSubView(null)} style={{ background: "#f0f0f0" }}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center" style={{ color: "#000" }}>{selectedInvoice?.number || selectedDoc?.title.replace(/^Счет\s*(№|N)?\s*/i, "") || "Просмотр"}</span>
                    <div className="nav-bar-right">
                        <button className="nav-bar-btn-circle" onClick={() => setSubView("invoiceForm")} style={{ background: "#f0f0f0" }}>
                            <Icon name="edit" />
                        </button>
                    </div>
                </div>
            </header>

            <div className="content-area" style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px)", paddingBottom: selectedInvoice ? "80px" : "0", overflow: "hidden" }}>
                {/* Compact Info Bar — Forced Light Theme for contrast */}
                {selectedInvoice && (
                    <div style={{ padding: "10px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "#fdfdfd", borderBottom: "1px solid #eee", flexShrink: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <span style={{ display: "inline-block", padding: "3px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, color: "#fff", background: statusColors[selectedInvoice.status] || "#8E8E93", textTransform: "uppercase" }}>
                                {statusLabels[selectedInvoice.status] || selectedInvoice.status}
                            </span>
                            <span style={{ fontSize: "15px", fontWeight: 700, color: "#000" }}>{formatMoney(selectedInvoice.total_amount)} ₸</span>
                        </div>
                        <span style={{ fontSize: "13px", color: "#666", fontWeight: 500, maxWidth: "50%", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{selectedInvoice.client_name}</span>
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
                            <div style={{ width: "32px", height: "32px", border: "3px solid #007AFF", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite", marginBottom: "12px" }} />
                            <div style={{ fontSize: "14px", color: "var(--text-secondary)" }}>Загрузка документа...</div>
                        </div>
                    )}

                    {previewPages.length > 0 ? (
                        <div style={{ padding: "8px" }}>
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

            {/* Floating Bottom Action Bar — Forced Light Theme */}
            {selectedInvoice && (
                <div style={{
                    position: "fixed",
                    bottom: 0, left: 0, right: 0,
                    background: "#fff",
                    borderTop: "1px solid #eee",
                    padding: "12px 16px",
                    paddingBottom: "max(12px, env(safe-area-inset-bottom))",
                    display: "flex",
                    gap: "8px",
                    zIndex: 100,
                    boxShadow: "0 -4px 12px rgba(0,0,0,0.05)"
                }}>
                    {selectedInvoice.status !== "paid" && (
                        <button
                            onClick={() => markInvoicePaid(selectedInvoice.id)}
                            style={{ flex: 1, height: "48px", borderRadius: "12px", border: "none", background: "#34C759", color: "#fff", fontSize: "15px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
                        >
                            <Icon name="check_circle" /> Оплачен
                        </button>
                    )}

                    {selectedInvoice.status === "draft" && (
                        <button
                            onClick={() => markInvoiceSent(selectedInvoice.id)}
                            style={{ flex: 1, height: "48px", borderRadius: "12px", border: "none", background: "#FF9500", color: "#fff", fontSize: "15px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
                        >
                            <Icon name="send" /> Отправлен
                        </button>
                    )}
                </div>
            )}
        </>
    );
}
