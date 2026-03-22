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
                    <div className="dashboard-label" style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginTop: "4px" }}>
                        <div style={{ width: "22px", height: "22px", borderRadius: "50%", background: "#FF9500", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>
                            <Icon name="schedule" style={{ fontSize: "14px" }} /> 
                        </div>
                        Ожидается
                    </div>
                </div>
            )}

            {summary.overdue > 0 && (
                <div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.overdue)} ₸</div>
                    <div className="dashboard-label" style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginTop: "4px" }}>
                        <div style={{ width: "22px", height: "22px", borderRadius: "50%", background: "var(--ios-red)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>
                            <Icon name="priority_high" style={{ fontSize: "14px", fontWeight: 900 }} /> 
                        </div>
                        Просрочено
                    </div>
                </div>
            )}

            {summary.paid_this_month > 0 && (
                <div>
                    <div className="dashboard-value" style={{ fontSize: "32px", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{formatMoney(summary.paid_this_month)} ₸</div>
                    <div className="dashboard-label" style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)", marginTop: "4px" }}>
                        <div style={{ width: "22px", height: "22px", borderRadius: "50%", background: "var(--ios-green)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>
                            <Icon name="check" style={{ fontSize: "14px", fontWeight: 800 }} /> 
                        </div>
                        Получено
                    </div>
                </div>
            )}
        </div>
    );
}
