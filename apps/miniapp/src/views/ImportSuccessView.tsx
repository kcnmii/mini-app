import React from "react";
import { Icon } from "../components/Common";

interface MatchResult {
    transaction_id: number;
    matched: boolean;
    invoice_id: number | null;
    invoice_number: string | null;
    client_name: string | null;
}

interface ImportResponse {
    added_count: number;
    matched_count: number;
    matches: MatchResult[];
}

interface ImportSuccessViewProps {
    result: ImportResponse | null;
    onClose: () => void;
}

export function ImportSuccessView({ result, onClose }: ImportSuccessViewProps) {
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

            <div className="content-area" style={{ flex: 1, padding: "32px 16px", display: "flex", flexDirection: "column", alignItems: "center", gap: "24px" }}>
                {!result ? (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", minHeight: "300px", gap: "16px" }}>
                        <div style={{ width: 40, height: 40, border: "3px solid var(--tg-theme-button-color, #007AFF)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                        <div style={{ color: "var(--text-secondary)", fontSize: "16px", fontWeight: 500 }}>Обработка выписки...</div>
                        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                    </div>
                ) : (
                    <>
                        <div style={{
                            width: 80, height: 80, borderRadius: "40px",
                            background: "var(--tg-theme-button-color, #007aff)",
                            color: "white", display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "40px", marginBottom: "8px"
                        }}>
                            <Icon name="check" />
                        </div>

                        <div style={{ textAlign: "center" }}>
                            <h1 style={{ fontSize: "24px", fontWeight: 700, margin: "0 0 8px 0" }}>Выписка загружена</h1>
                            <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "15px", lineHeight: "20px" }}>
                                Мы успешно обработали файл и сохранили все операции.
                            </p>
                        </div>

                        <div className="ios-group" style={{ alignSelf: "stretch", marginTop: "16px" }}>
                            <div className="ios-cell">
                                <span style={{ color: "var(--text)" }}>Новых операций</span>
                                <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>{result.added_count}</span>
                            </div>
                            <div className="ios-cell">
                                <span style={{ color: "var(--text)" }}>Оплачено счетов</span>
                                <span style={{ color: "var(--tg-theme-button-color, #007aff)", fontWeight: 700 }}>{result.matched_count}</span>
                            </div>
                        </div>

                        {result.matches && result.matches.length > 0 && (
                            <div style={{ alignSelf: "stretch", marginTop: "16px" }}>
                                <h3 style={{ margin: "0 0 12px 0", fontSize: "15px", color: "var(--text-secondary)", textTransform: "none", letterSpacing: "normal" }}>Успешные совпадения:</h3>
                                <div className="ios-group">
                                    {result.matches.map((m, idx) => (
                                        <div key={idx} className="ios-cell" style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px", padding: "12px 16px" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                                                <span style={{ fontWeight: 600, fontSize: "16px" }}>Счёт №{m.invoice_number}</span>
                                                <span style={{ color: "#34C759", fontWeight: 600 }}><Icon name="task_alt" style={{ fontSize: "18px", verticalAlign: "middle" }} /> Оплачен</span>
                                            </div>
                                            <span style={{ color: "var(--text-secondary)", fontSize: "14px" }}>{m.client_name}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        <div className="spacer-24" />
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
