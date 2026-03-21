import React, { useState } from "react";
import { Icon } from "../components/Common";
import { getBankByIIK } from "../utils/bankAutofill";
import { Toggle } from "../components/Common";

interface AddBankAccountViewProps {
    setSubView: (v: any) => void;
    onAddAccount: (acc: { account_number: string; bank_name: string; bic: string; kbe: string; is_default: boolean }) => Promise<void>;
    busy: string;
}

export function AddBankAccountView({
    setSubView,
    onAddAccount,
    busy
}: AddBankAccountViewProps) {
    const [account, setAccount] = useState("");
    const [bankName, setBankName] = useState("");
    const [bic, setBic] = useState("");
    const [kbe, setKbe] = useState("19"); // "19" is a common default for KBe in Kazakhstan (private companies)
    const [isDefault, setIsDefault] = useState(true);

    const handleSave = async () => {
        if (!account) return;
        await onAddAccount({
            account_number: account,
            bank_name: bankName,
            bic: bic,
            kbe: kbe,
            is_default: isDefault
        });
    };

    return (
        <>
            <header className="nav-bar animate-slide-up">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">Добавить счет</span>
                    <button className="nav-bar-btn-circle" onClick={handleSave} disabled={busy !== "idle"}>
                        <Icon name="check" />
                    </button>
                </div>
            </header>
            <div className="content-area animate-slide-up">
                <div className="section-title" style={{ paddingTop: 8 }}>Реквизиты счета</div>
                <div className="ios-group">
                    <div className="form-field">
                        <input
                            placeholder="IBAN (Например, KZ...)"
                            value={account}
                            onChange={(e) => {
                                const val = e.target.value;
                                const info = getBankByIIK(val);
                                setAccount(val);
                                if (info) {
                                    setBic(info.bik);
                                    setBankName(info.name);
                                }
                            }}
                        />
                    </div>
                    <div className="form-field"><input placeholder="БИК банка" value={bic} onChange={(e) => setBic(e.target.value)} /></div>
                    <div className="form-field"><input placeholder="Название банка" value={bankName} onChange={(e) => setBankName(e.target.value)} /></div>
                    <div className="form-field"><input placeholder="Кбе" value={kbe} onChange={(e) => setKbe(e.target.value)} /></div>
                </div>
                <div className="section-title">Состояние</div>
                <div className="ios-group">
                    <div className="toggle-row">
                        <span className="toggle-row-label">Сделать основным</span>
                        <Toggle checked={isDefault} onChange={() => setIsDefault(!isDefault)} />
                    </div>
                </div>
                <div className="form-hint">Этот счет будет отображаться во всех новых выставляемых вами счетах-фактурах.</div>
            </div>
        </>
    );
}
