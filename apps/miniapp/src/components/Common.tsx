import React from "react";

export function Icon({ name, filled, className, style }: { name: string; filled?: boolean; className?: string; style?: React.CSSProperties }) {
    return (
        <span className={`material-symbols-outlined${filled ? " filled" : ""}${className ? ` ${className}` : ""}`} style={style}>
            {name}
        </span>
    );
}

export function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
    return (
        <button
            type="button"
            className={`ios-switch-track${checked ? " on" : ""}`}
            disabled={disabled}
            onClick={() => onChange(!checked)}
        >
            <span className="ios-switch-knob" />
        </button>
    );
}

export function Checkbox({ checked, onChange }: { checked: boolean; onChange: (e: React.MouseEvent) => void }) {
    return (
        <div className={`ios-checkbox${checked ? " checked" : ""}`} onClick={onChange}>
            <Icon name="check" style={{ fontSize: "16px", color: "#fff", fontWeight: "900" }} />
        </div>
    );
}

export function ActionSheet({ isOpen, onClose, title, actions }: { isOpen: boolean; onClose: () => void; title?: string; actions: { label: string; onClick: () => void; danger?: boolean; bold?: boolean }[] }) {
    if (!isOpen) return null;
    return (
        <div className="action-sheet-overlay" onClick={onClose}>
            <div className="action-sheet" onClick={(e) => e.stopPropagation()}>
                <div className="action-sheet-group">
                    {title && <div style={{ padding: "16px", fontSize: "13px", color: "var(--text-secondary)", textAlign: "center", borderBottom: "1px solid var(--separator)" }}>{title}</div>}
                    {actions.map((act, i) => (
                        <button key={i} className={`action-sheet-btn${act.danger ? " danger" : ""}${act.bold ? " bold" : ""}`} onClick={() => { act.onClick(); onClose(); }}>
                            {act.label}
                        </button>
                    ))}
                </div>
                <div className="action-sheet-group">
                    <button className="action-sheet-btn bold" onClick={onClose}>Отмена</button>
                </div>
            </div>
        </div>
    );
}
