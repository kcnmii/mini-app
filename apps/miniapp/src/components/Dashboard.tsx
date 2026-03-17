import React from "react";
import { DashboardSummary } from "../types";
import { formatMoney } from "../utils";

interface DashboardProps {
    summary: DashboardSummary;
}

export function Dashboard({ summary }: DashboardProps) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", padding: "12px 20px 8px" }}>
            <div>
                <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "4px" }}>Ожидается</div>
                <div style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.awaiting)} ₸</div>
            </div>

            {summary.overdue > 0 && (
                <div>
                    <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--ios-red)", marginBottom: "4px" }}>Просрочено</div>
                    <div style={{ fontSize: "32px", fontWeight: 700, color: "var(--ios-red)", letterSpacing: "-0.02em" }}>{formatMoney(summary.overdue)} ₸</div>
                </div>
            )}

            <div>
                <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "4px" }}>Получено</div>
                <div style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.paid_this_month)} ₸</div>
            </div>
        </div>
    );
}
