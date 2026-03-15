import React from "react";
import { InvoiceRecord } from "../types";
import { formatMoney } from "../utils";
import { StatusBadge } from "./StatusBadge";
import { Icon } from "./Common";

interface InvoiceRowProps {
    invoice: InvoiceRecord;
    onClick: (id: number) => void;
    showDate?: boolean;
}

export function InvoiceRow({ invoice, onClick, showDate = true }: InvoiceRowProps) {
    return (
        <div className="doc-row clickable" key={invoice.id} onClick={() => onClick(invoice.id)}>
            <div className="doc-row-left">
                <div className="doc-row-title">{invoice.number} · {invoice.client_name || "—"}</div>
                <div className="doc-row-meta" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <StatusBadge status={invoice.status} />
                    <span className="doc-row-date">{formatMoney(invoice.total_amount)} ₸</span>
                    {showDate && (
                        <span className="doc-row-date">
                            {new Date(invoice.created_at).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}
                        </span>
                    )}
                </div>
            </div>
            <div className="ios-row-right"><Icon name="chevron_right" /></div>
        </div>
    );
}
