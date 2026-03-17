import React from "react";
import { Icon } from "../components/Common";

type DateFilterType = "today" | "week" | "month" | "all" | "custom";
type DateFilter = { type: DateFilterType; from?: string; to?: string };

interface DateFilterViewProps {
    dateFilter: DateFilter;
    setDateFilter: React.Dispatch<React.SetStateAction<DateFilter>>;
    onClose: () => void;
}

export function DateFilterView({ dateFilter, setDateFilter, onClose }: DateFilterViewProps) {
    const pick = (type: DateFilterType) => { setDateFilter({ type }); onClose(); };

    return (
        <>
            <header className="nav-bar">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={onClose}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">Период</span>
                    <div className="nav-bar-right" />
                </div>
            </header>
            <div className="content-area">
                <div className="section-title" style={{ paddingTop: 8 }}>Выберите период</div>
                <div className="ios-group">
                    <button className="ios-row" onClick={() => pick("today")}>
                        <div className="ios-row-content"><div className="ios-row-title">Сегодня</div></div>
                        {dateFilter.type === "today" && <Icon name="check" style={{ color: "var(--primary)" }} />}
                    </button>
                    <button className="ios-row" onClick={() => pick("week")}>
                        <div className="ios-row-content"><div className="ios-row-title">Неделя</div></div>
                        {dateFilter.type === "week" && <Icon name="check" style={{ color: "var(--primary)" }} />}
                    </button>
                    <button className="ios-row" onClick={() => pick("month")}>
                        <div className="ios-row-content"><div className="ios-row-title">Месяц</div></div>
                        {dateFilter.type === "month" && <Icon name="check" style={{ color: "var(--primary)" }} />}
                    </button>
                    <button className="ios-row" onClick={() => pick("all")}>
                        <div className="ios-row-content"><div className="ios-row-title">За все время</div></div>
                        {dateFilter.type === "all" && <Icon name="check" style={{ color: "var(--primary)" }} />}
                    </button>
                    <button className="ios-row" onClick={() => setDateFilter(d => ({ ...d, type: "custom" }))}>
                        <div className="ios-row-content"><div className="ios-row-title">Кастомный период</div></div>
                        {dateFilter.type === "custom" && <Icon name="check" style={{ color: "var(--primary)" }} />}
                    </button>
                </div>

                {dateFilter.type === "custom" && (
                    <>
                        <div className="section-title">Диапазон дат</div>
                        <div className="ios-group">
                            <div className="form-field">
                                <span className="form-field-label">Начало</span>
                                <input
                                    type="date"
                                    className="native-date-input"
                                    value={dateFilter.from?.split("T")[0] || ""}
                                    onChange={(e) => setDateFilter(d => ({ ...d, from: e.target.value ? new Date(e.target.value).toISOString() : undefined }))}
                                />
                            </div>
                            <div className="field-divider" />
                            <div className="form-field">
                                <span className="form-field-label">Конец</span>
                                <input
                                    type="date"
                                    className="native-date-input"
                                    value={dateFilter.to?.split("T")[0] || ""}
                                    onChange={(e) => setDateFilter(d => ({ ...d, to: e.target.value ? new Date(e.target.value).toISOString() : undefined }))}
                                />
                            </div>
                        </div>
                        <div style={{ padding: "24px 16px" }}>
                            <button className="action-btn-main" onClick={onClose}>Применить</button>
                        </div>
                    </>
                )}
            </div>
        </>
    );
}
