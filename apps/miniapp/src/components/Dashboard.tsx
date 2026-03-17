import React from "react";
import { DashboardSummary } from "../types";
import { formatMoney } from "../utils";

interface DashboardProps {
    summary: DashboardSummary;
}

export function Dashboard({ summary }: DashboardProps) {
    return (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", padding: "12px 16px 0" }}>
            <div style={{
                background: "linear-gradient(135deg, #FF9500 0%, #FF6B00 100%)",
                borderRadius: "16px",
                padding: "16px",
                color: "#fff",
                gridColumn: summary.overdue > 0 ? "1" : "1 / -1"
            }}>
                <div style={{ fontSize: "13px", opacity: 0.85, marginBottom: "4px" }}>Ожидается</div>
                <div style={{ fontSize: "22px", fontWeight: 700 }}>{formatMoney(summary.awaiting)} ₸</div>
            </div>

            {summary.overdue > 0 && (
                <div style={{ background: "linear-gradient(135deg, #FF3B30 0%, #D32F2F 100%)", borderRadius: "16px", padding: "16px", color: "#fff" }}>
                    <div style={{ fontSize: "13px", opacity: 0.85, marginBottom: "4px" }}>
                        Просрочено{summary.overdue_count > 0 && ` (${summary.overdue_count})`}
                    </div>
                    <div style={{ fontSize: "22px", fontWeight: 700 }}>{formatMoney(summary.overdue)} ₸</div>
                </div>
            )}

            <div style={{
                background: "linear-gradient(135deg, #34C759 0%, #28A745 100%)",
                borderRadius: "16px",
                padding: "16px",
                color: "#fff",
                gridColumn: "1 / -1"
            }}>
                <div style={{ fontSize: "13px", opacity: 0.85, marginBottom: "4px" }}>Получено</div>
                <div style={{ fontSize: "22px", fontWeight: 700 }}>{formatMoney(summary.paid_this_month)} ₸</div>
            </div>
        </div>
    );
}
