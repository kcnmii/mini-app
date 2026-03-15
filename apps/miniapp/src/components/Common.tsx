import React from "react";

export function Icon({ name, filled, className }: { name: string; filled?: boolean; className?: string }) {
    return (
        <span className={`material-symbols-outlined${filled ? " filled" : ""}${className ? ` ${className}` : ""}`}>
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
