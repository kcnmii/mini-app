import React from "react";

const statusLabels: Record<string, string> = {
    draft: "Черновик",
    sent: "Отправлен",
    paid: "Оплачен",
    overdue: "Просрочен"
};

const statusColors: Record<string, string> = {
    draft: "#8E8E93",
    sent: "#FF9500",
    paid: "#34C759",
    overdue: "#FF3B30"
};

export function StatusBadge({ status }: { status: string }) {
    const label = statusLabels[status] || status;
    const color = statusColors[status] || "#8E8E93";

    return (
        <span style={{
            display: "inline-block",
            padding: "2px 8px",
            borderRadius: "6px",
            fontSize: "11px",
            fontWeight: 600,
            color: "#fff",
            background: color
        }}>
            {label}
        </span>
    );
}
