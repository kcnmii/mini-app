import React, { useState } from "react";
import { Icon } from "../components/Common";

export type DocTypeFilter = "all" | "invoice" | "avr" | "waybill";

export const typeFilterOptions = [
    { id: 'all', label: 'Все документы' },
    { id: 'invoice', label: 'Счета на оплату' },
    { id: 'avr', label: 'АВР (Акты)' },
    { id: 'waybill', label: 'Накладные на отпуск' }
] as const;

export const statusFilters = ["all", "sent", "overdue", "paid", "draft"] as const;
export const statusFilterLabels: Record<string, string> = { all: "Все", sent: "Отправленные", overdue: "Просроченные", paid: "Оплаченные", draft: "Черновики" };

interface DocumentFilterViewProps {
    currentStatusFilter: string;
    currentTypeFilter: DocTypeFilter;
    onApply: (status: string, type: DocTypeFilter) => void;
    onClose: () => void;
    isClosing: boolean;
}

export function DocumentFilterView({
    currentStatusFilter,
    currentTypeFilter,
    onApply,
    onClose,
    isClosing
}: DocumentFilterViewProps) {
    const [tempType, setTempType] = useState<DocTypeFilter>(currentTypeFilter);
    const [tempStatus, setTempStatus] = useState<string>(currentStatusFilter);

    return (
        <div style={{ position: "fixed", inset: 0, background: "var(--bg)", zIndex: 1200, display: "flex", flexDirection: "column", height: "100dvh" }} className={isClosing ? "animate-slide-down" : "animate-slide-up"}>
            <header className="nav-bar">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={onClose}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">Фильтры</span>
                    <div className="nav-bar-right" style={{ width: 44 }} />
                </div>
            </header>
            <div className="content-area" style={{ overflowY: "auto", flex: 1 }}>
                <div className="section-title" style={{ paddingTop: 8 }}>Тип документа</div>
                <div className="ios-group">
                    {typeFilterOptions.map((opt, i) => (
                        <React.Fragment key={opt.id}>
                            <button className="ios-row" onClick={() => setTempType(opt.id)}>
                                <div className="ios-row-content">
                                    <div className="ios-row-title">{opt.label}</div>
                                </div>
                                {tempType === opt.id && <Icon name="check" style={{ color: "var(--primary)" }} />}
                            </button>
                            {i < typeFilterOptions.length - 1 && <div className="field-divider" />}
                        </React.Fragment>
                    ))}
                </div>

                {["all", "invoice"].includes(tempType) && (
                    <>
                        <div className="section-title">Статус счета</div>
                        <div className="ios-group">
                            {statusFilters.map((status, i) => (
                                <React.Fragment key={status}>
                                    <button className="ios-row" onClick={() => setTempStatus(status)}>
                                        <div className="ios-row-content">
                                            <div className="ios-row-title">{statusFilterLabels[status]}</div>
                                        </div>
                                        {tempStatus === status && <Icon name="check" style={{ color: "var(--primary)" }} />}
                                    </button>
                                    {i < statusFilters.length - 1 && <div className="field-divider" />}
                                </React.Fragment>
                            ))}
                        </div>
                    </>
                )}
                
                <div style={{ padding: "24px 16px" }}>
                    <button className="action-btn-main" onClick={() => onApply(tempStatus, tempType)}>Применить</button>
                </div>
            </div>
        </div>
    );
}
