import React from "react";
import { DashboardSummary } from "../types";
import { formatMoney } from "../utils";

interface DashboardProps {
    summary: DashboardSummary;
}

export function Dashboard({ summary }: DashboardProps) {
    const allZero = summary.awaiting === 0 && summary.overdue === 0 && summary.paid_this_month === 0;

    return (
        <div className="dashboard-hero" style={{ display: "flex", flexDirection: "column", gap: "16px", padding: "12px 20px 8px" }}>
            {(summary.awaiting > 0 || allZero) && (
                <div>
                    <div className="dashboard-label" style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "4px" }}>Ожидается</div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.awaiting)} ₸</div>
                </div>
            )}

            {summary.overdue > 0 && (
                <div>
                    <div className="dashboard-label" style={{ fontSize: "14px", fontWeight: 500, color: "var(--ios-red)", marginBottom: "4px" }}>Просрочено</div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--ios-red)", letterSpacing: "-0.02em" }}>{formatMoney(summary.overdue)} ₸</div>
                </div>
            )}

            {summary.paid_this_month > 0 && (
                <div>
                    <div className="dashboard-label" style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "4px" }}>Получено</div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.paid_this_month)} ₸</div>
                </div>
            )}
        </div>
    );
}
