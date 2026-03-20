import React, { useState } from "react";
import { Icon } from "../components/Common";
import { request } from "../utils";

interface CandidateInvoice {
    invoice_id: number;
    invoice_number: string;
    total_amount: number;
    client_name: string;
}

interface AutoMatchedInvoice {
    invoice_id: number;
    invoice_number: string;
    client_name: string;
    amount: number;
    sender_name: string;
}

interface NeedsAttentionItem {
    sender_name: string;
    sender_bin: string;
    amount: number;
    date: string;
    description: string;
    doc_num: string;
    candidate_invoices: CandidateInvoice[];
}

interface ImportResponse {
    total_incomes: number;
    auto_matched_count: number;
    ignored_count: number;
    auto_matched: AutoMatchedInvoice[];
    needs_attention: NeedsAttentionItem[];
}

interface ImportSuccessViewProps {
    result: ImportResponse | null;
    onClose: () => void;
    onRefresh: () => void;
}

function formatMoney(n: number) {
    return n.toLocaleString("ru-KZ", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export function ImportSuccessView({ result, onClose, onRefresh }: ImportSuccessViewProps) {
    const [manuallyMatched, setManuallyMatched] = useState<Set<number>>(new Set());
    const [matchingIdx, setMatchingIdx] = useState<number | null>(null);

    const handleManualMatch = async (attentionIdx: number, invoiceId: number, item: NeedsAttentionItem) => {
        try {
            setMatchingIdx(attentionIdx);
            await request<any>("/banks/manual-match", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    invoice_id: invoiceId,
                    amount: item.amount,
                    date: item.date,
                    sender_name: item.sender_name,
                    doc_num: item.doc_num,
                    description: item.description
                })
            });
            setManuallyMatched(prev => new Set(prev).add(attentionIdx));
            onRefresh();
        } catch (err) {
            console.error("Manual match failed:", err);
        } finally {
            setMatchingIdx(null);
        }
    };

    return (
        <div className="view-container" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
            <div className="nav-bar">
                <div className="nav-bar-detail" style={{ position: "relative", justifyContent: "center" }}>
                    <button className="nav-bar-btn-circle" onClick={onClose} style={{ position: "absolute", left: 16 }}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">
                        Импорт 1С
                    </span>
                </div>
            </div>

            <div className="content-area" style={{ flex: 1, overflow: "auto", padding: "32px 16px", display: "flex", flexDirection: "column", alignItems: "center", gap: "24px" }}>
                {!result ? (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", minHeight: "300px", gap: "16px" }}>
                        <div style={{ width: 40, height: 40, border: "3px solid var(--tg-theme-button-color, #007AFF)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                        <div style={{ color: "var(--text-secondary)", fontSize: "16px", fontWeight: 500 }}>Обработка выписки...</div>
                        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                    </div>
                ) : (
                    <>
                        {/* Success icon */}
                        <div style={{
                            width: 80, height: 80, borderRadius: "40px",
                            background: result.auto_matched_count > 0 ? "#34C759" : "var(--tg-theme-button-color, #007aff)",
                            color: "white", display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "40px", marginBottom: "8px"
                        }}>
                            <Icon name={result.auto_matched_count > 0 ? "check" : "info"} />
                        </div>

                        <div style={{ textAlign: "center" }}>
                            <h1 style={{ fontSize: "24px", fontWeight: 700, margin: "0 0 8px 0" }}>
                                {result.auto_matched_count > 0
                                    ? "Выписка обработана"
                                    : (result.needs_attention.length > 0 ? "Требует внимания" : "Совпадений не найдено")}
                            </h1>
                            <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "15px", lineHeight: "20px" }}>
                                {result.auto_matched_count > 0
                                    ? "Счета были автоматически отмечены как оплаченные."
                                    : (result.needs_attention.length > 0
                                        ? "Мы нашли переводы от ваших клиентов, но суммы не совпадают со счетами. Проверьте их ниже."
                                        : "В выписке не нашлось платежей от ваших текущих клиентов или совпадающих неоплаченных счетов. Чужие или старые операции проигнорированы.")}
                            </p>
                        </div>

                        {/* Stats */}
                        <div className="ios-group" style={{ alignSelf: "stretch", marginTop: "16px" }}>
                            <div className="ios-cell">
                                <span style={{ color: "var(--text)" }}>Поступлений в выписке</span>
                                <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>{result.total_incomes}</span>
                            </div>
                            <div className="ios-cell">
                                <span style={{ color: "var(--text)" }}>Оплачено автоматически</span>
                                <span style={{ color: "#34C759", fontWeight: 700 }}>{result.auto_matched_count}</span>
                            </div>
                            {result.needs_attention.length > 0 && (
                                <div className="ios-cell">
                                    <span style={{ color: "var(--text)" }}>Требует внимания</span>
                                    <span style={{ color: "#FF9500", fontWeight: 700 }}>{result.needs_attention.length}</span>
                                </div>
                            )}
                            <div className="ios-cell">
                                <span style={{ color: "var(--text)" }}>Пропущено (не ваши клиенты)</span>
                                <span style={{ color: "var(--text-secondary)" }}>{result.ignored_count}</span>
                            </div>
                        </div>

                        {/* Auto-matched list */}
                        {result.auto_matched.length > 0 && (
                            <div style={{ alignSelf: "stretch", marginTop: "8px" }}>
                                <h3 style={{ margin: "0 0 12px 0", fontSize: "15px", color: "var(--text-secondary)", textTransform: "none", letterSpacing: "normal" }}>✅ Оплачены автоматически</h3>
                                <div className="ios-group">
                                    {result.auto_matched.map((m, idx) => (
                                        <div key={idx} className="ios-cell" style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px", padding: "12px 16px" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                                                <span style={{ fontWeight: 600, fontSize: "15px" }}>Счёт №{m.invoice_number}</span>
                                                <span style={{ color: "#34C759", fontWeight: 600, fontSize: "15px" }}>{formatMoney(m.amount)} ₸</span>
                                            </div>
                                            <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{m.client_name}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Needs attention list */}
                        {result.needs_attention.length > 0 && (
                            <div style={{ alignSelf: "stretch", marginTop: "8px" }}>
                                <h3 style={{ margin: "0 0 12px 0", fontSize: "15px", color: "#FF9500", textTransform: "none", letterSpacing: "normal" }}>⚠️ Требует внимания</h3>
                                <div className="ios-group">
                                    {result.needs_attention.map((item, idx) => (
                                        <div key={idx} style={{ padding: "12px 16px", borderBottom: idx < result.needs_attention.length - 1 ? "1px solid var(--border)" : "none" }}>
                                            {manuallyMatched.has(idx) ? (
                                                <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#34C759" }}>
                                                    <Icon name="task_alt" style={{ fontSize: "20px" }} />
                                                    <span style={{ fontWeight: 600 }}>Привязано!</span>
                                                </div>
                                            ) : (
                                                <>
                                                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                                                        <span style={{ fontWeight: 600, fontSize: "15px" }}>{item.sender_name}</span>
                                                        <span style={{ fontWeight: 700, fontSize: "15px" }}>{formatMoney(item.amount)} ₸</span>
                                                    </div>
                                                    <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                                                        {item.description.substring(0, 100)}{item.description.length > 100 ? "..." : ""}
                                                    </div>

                                                    {item.candidate_invoices.length > 0 ? (
                                                        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                                            <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Привязать к счёту:</span>
                                                            {item.candidate_invoices.map(ci => (
                                                                <button
                                                                    key={ci.invoice_id}
                                                                    onClick={() => handleManualMatch(idx, ci.invoice_id, item)}
                                                                    disabled={matchingIdx === idx}
                                                                    style={{
                                                                        display: "flex", justifyContent: "space-between", alignItems: "center",
                                                                        padding: "10px 12px", borderRadius: "10px",
                                                                        border: "1px solid var(--border)", background: "var(--bg-secondary, #f5f5f5)",
                                                                        cursor: "pointer", fontSize: "14px", width: "100%"
                                                                    }}
                                                                >
                                                                    <span>№{ci.invoice_number} — {formatMoney(ci.total_amount)} ₸</span>
                                                                    <Icon name="link" style={{ fontSize: "18px", color: "var(--tg-theme-button-color, #007aff)" }} />
                                                                </button>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <div style={{ fontSize: "13px", color: "var(--text-secondary)", fontStyle: "italic" }}>
                                                            Нет неоплаченных счетов для этого клиента
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div style={{ height: "80px" }} />
                    </>
                )}
            </div>

            {/* Bottom Action Bar */}
            {result && (
                <div className="invoice-footer" style={{ background: "#fff", borderTop: "1px solid #eee", marginTop: "auto" }}>
                    <div className="invoice-footer-inner">
                        <button className="invoice-send-btn" onClick={onClose} style={{ width: "100%" }}>
                            Отлично
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
