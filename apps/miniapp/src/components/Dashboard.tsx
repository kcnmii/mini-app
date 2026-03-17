import React from "react";
import { DashboardSummary } from "../types";
import { formatMoney } from "../utils";

interface DashboardProps {
    summary: DashboardSummary;
}

export function Dashboard({ summary }: DashboardProps) {
    return (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "24px", padding: "16px 16px 8px" }}>
            <div>
                <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "2px" }}>Ожидается</div>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#FF9500" }}>{formatMoney(summary.awaiting)} ₸</div>
            </div>

            {summary.overdue > 0 && (
                <div>
                    <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "2px" }}>Просрочено</div>
                    <div style={{ fontSize: "24px", fontWeight: 700, color: "#FF3B30" }}>{formatMoney(summary.overdue)} ₸</div>
                </div>
            )}

            <div>
                <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "2px" }}>Получено</div>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#34C759" }}>{formatMoney(summary.paid_this_month)} ₸</div>
            </div>
        </div>
    );
}
