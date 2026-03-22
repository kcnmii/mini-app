import React from "react";
import { InvoiceRecord } from "../types";
import { formatMoney } from "../utils";
import { StatusBadge } from "./StatusBadge";
import { Icon, Checkbox } from "./Common";

interface InvoiceRowProps {
    invoice: InvoiceRecord;
    onClick: (id: number) => void;
    showDate?: boolean;
    isEditMode?: boolean;
    isSelected?: boolean;
    onSelect?: (id: number) => void;
}

export function InvoiceRow({ invoice, onClick, showDate = true, isEditMode, isSelected, onSelect }: InvoiceRowProps) {
    const handleRowClick = () => {
        if (isEditMode && onSelect) {
            onSelect(invoice.id);
        } else {
            onClick(invoice.id);
        }
    };

    return (
        <div className={`selectable-row-container${isEditMode ? " edit-mode" : ""}`} onClick={handleRowClick}>
            <div className="selectable-checkbox-wrap">
                <Checkbox checked={!!isSelected} onChange={() => {}} />
            </div>
            <div className="doc-row clickable" style={{ flex: 1 }}>
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
                {!isEditMode && <div className="ios-row-right"><Icon name="chevron_right" /></div>}
            </div>
        </div>
    );
}
