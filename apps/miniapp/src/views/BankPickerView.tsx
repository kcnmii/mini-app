import React from "react";
import { Icon } from "../components/Common";
import type { SupplierProfileData, BankAccount } from "../types";

interface BankPickerViewProps {
    bankAccounts: BankAccount[];
    selectedBankAccountId: number | null;
    setSelectedBankAccountId: React.Dispatch<React.SetStateAction<number | null>>;
    onClose: () => void;
    onAddAccount: () => void;
}

export function BankPickerView({
    bankAccounts,
    selectedBankAccountId,
    setSelectedBankAccountId,
    onClose,
    onAddAccount,
}: BankPickerViewProps) {
    return (
        <>
            <header className="nav-bar">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={onClose}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">Банковский счёт</span>
                    <div className="nav-bar-right" />
                </div>
            </header>
            <div className="content-area">
                <div className="section-title" style={{ paddingTop: 8 }}>Выберите счёт</div>
                <div className="ios-group">
                    <button className="ios-row" onClick={() => { setSelectedBankAccountId(null); onClose(); }}>
                        <div className="ios-row-content"><div className="ios-row-title">Все счета</div></div>
                        {selectedBankAccountId === null && <Icon name="check" style={{ color: "var(--primary)" }} />}
                    </button>
                    {bankAccounts.map(ba => (
                        <button className="ios-row" key={ba.id} onClick={() => { setSelectedBankAccountId(ba.id); onClose(); }}>
                            <div className="ios-row-content">
                                <div className="ios-row-title">{ba.bank_name || ba.account_number}</div>
                                <div className="ios-row-subtitle" style={{ textTransform: "uppercase" }}>{ba.account_number}</div>
                            </div>
                            {selectedBankAccountId === ba.id && <Icon name="check" style={{ color: "var(--primary)" }} />}
                        </button>
                    ))}
                </div>
                <div style={{ padding: "24px 16px" }}>
                    <button className="dashed-add-btn" onClick={onAddAccount}>
                        <Icon name="add_circle" /> Добавить счёт
                    </button>
                </div>
            </div>
        </>
    );
}
