import React from "react";
import { DashboardSummary } from "../types";
import { formatMoney } from "../utils";
import { Icon } from "./Common";

interface DashboardProps {
    summary: DashboardSummary;
}

export function Dashboard({ summary }: DashboardProps) {
    const allZero = summary.awaiting === 0 && summary.overdue === 0 && summary.paid_this_month === 0;

    return (
        <div className="dashboard-hero" style={{ display: "flex", flexDirection: "column", gap: "16px", padding: "12px 20px 8px" }}>
            {(summary.awaiting > 0 || allZero) && (
                <div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.awaiting)} ₸</div>
                    <div className="dashboard-label" style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginTop: "2px" }}>
                        <Icon name="schedule" style={{ fontSize: "18px" }} /> 
                        Ожидается
                    </div>
                </div>
            )}

            {summary.overdue > 0 && (
                <div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--ios-red)", letterSpacing: "-0.02em" }}>{formatMoney(summary.overdue)} ₸</div>
                    <div className="dashboard-label" style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "14px", fontWeight: 500, color: "var(--ios-red)", marginTop: "2px" }}>
                        <Icon name="error_outline" style={{ fontSize: "18px" }} /> 
                        Просрочено
                    </div>
                </div>
            )}

            {summary.paid_this_month > 0 && (
                <div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.paid_this_month)} ₸</div>
                    <div className="dashboard-label" style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginTop: "2px" }}>
                        <Icon name="check_circle" style={{ fontSize: "18px" }} /> 
                        Получено
                    </div>
                </div>
            )}
        </div>
    );
}
