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
    if (!result) return null;

    return (
        <div className="view-container">
            <div className="nav-bar">
                <div className="nav-bar-inner" style={{ justifyContent: "center" }}>
                    <h2 style={{ fontSize: "17px", fontWeight: "600", margin: 0, textAlign: "center" }}>Импорт 1С</h2>
                    <button onClick={onClose} style={{ position: "absolute", right: 16, background: "none", border: "none", color: "var(--tg-theme-button-color, #007aff)", fontSize: "17px", fontWeight: 600 }}>
                        Готово
                    </button>
                </div>
            </div>

            <div className="content-area" style={{ padding: "32px 16px", display: "flex", flexDirection: "column", alignItems: "center", gap: "24px" }}>

                {/* Big success icon */}
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
                <button className="home-action-btn home-action-btn--primary" style={{ width: "100%" }} onClick={onClose}>
                    Отлично
                </button>
            </div>
        </div>
    );
}
