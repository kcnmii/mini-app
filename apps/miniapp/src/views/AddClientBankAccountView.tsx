import React from "react";
import { Icon } from "../components/Common";
import { Toggle } from "../components/Common";
import { getBankByIIK } from "../utils/bankAutofill";
import type { Client, ClientBankAccount } from "../types";

interface AddClientBankAccountViewProps {
    setSubView: (v: any) => void;
    clientBaDraft: ClientBankAccount;
    setClientBaDraft: React.Dispatch<React.SetStateAction<ClientBankAccount>>;
    saveClientBa: () => void;
    editingBaIndex: number | null;
    setClientDraft: React.Dispatch<React.SetStateAction<Client>>;
}

export function AddClientBankAccountView({
    setSubView,
    clientBaDraft,
    setClientBaDraft,
    saveClientBa,
    editingBaIndex,
    setClientDraft
}: AddClientBankAccountViewProps) {
    return (
        <>
            <header className="nav-bar animate-slide-up">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => setSubView("addClient")}>
                        <Icon name={editingBaIndex !== null ? "chevron_left" : "close"} className={editingBaIndex !== null ? "large-icon" : ""} />
                    </button>
                    <span className="nav-bar-title-center">Банковский счет</span>
                    <button className="nav-bar-btn-circle" onClick={saveClientBa}>
                        <Icon name="check" />
                    </button>
                </div>
            </header>
            <div className="content-area animate-slide-up">
                <div className="ios-group" style={{ marginTop: 16 }}>
                    <div className="form-field">
                        <input
                            placeholder="ИИК (Напр. KZ...)"
                            value={clientBaDraft.iic}
                            onChange={(e) => {
                                const val = e.target.value;
                                const info = getBankByIIK(val);
                                setClientBaDraft(c => ({
                                    ...c,
                                    iic: val,
                                    bank_name: info ? info.name : c.bank_name,
                                    bic: info ? info.bik : c.bic
                                }));
                            }}
                        />
                    </div>
                    <div className="form-field"><input placeholder="Наименование банка" value={clientBaDraft.bank_name} onChange={(e) => setClientBaDraft(c => ({ ...c, bank_name: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="БИК" value={clientBaDraft.bic} onChange={(e) => setClientBaDraft(c => ({ ...c, bic: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Кбе" value={clientBaDraft.kbe} onChange={(e) => setClientBaDraft(c => ({ ...c, kbe: e.target.value }))} /></div>
                    <div className="settings-row">
                        <span className="settings-row-label">Основной счет</span>
                        <Toggle checked={clientBaDraft.is_main} onChange={(v) => setClientBaDraft(c => ({ ...c, is_main: v }))} />
                    </div>
                </div>
                {editingBaIndex !== null && (
                    <div style={{ padding: "16px" }}>
                        <button className="destructive-btn" onClick={() => {
                            setClientDraft((c: Client) => ({ ...c, accounts: c.accounts.filter((_, i) => i !== editingBaIndex) }));
                            setSubView("addClient");
                        }}>Удалить счет</button>
                    </div>
                )}
            </div>
        </>
    );
}
