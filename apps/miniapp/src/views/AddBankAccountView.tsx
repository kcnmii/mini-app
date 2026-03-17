import React from "react";
import { Icon } from "../components/Common";
import { getBankByIIK } from "../utils/bankAutofill";
import { Toggle } from "../components/Common";
import type { SupplierProfileData } from "../types";

interface AddBankAccountViewProps {
    profile: SupplierProfileData;
    profileDraft: SupplierProfileData;
    setProfileDraft: React.Dispatch<React.SetStateAction<SupplierProfileData>>;
    setSubView: (v: any) => void;
    saveProfile: () => void;
    deleteBankAccount: () => void;
    busy: string;
}

export function AddBankAccountView({
    profile,
    profileDraft,
    setProfileDraft,
    setSubView,
    saveProfile,
    deleteBankAccount,
    busy
}: AddBankAccountViewProps) {
    return (
        <>
            <header className="nav-bar">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">Добавить счет</span>
                    <button className="nav-bar-btn-circle" onClick={() => { saveProfile(); setSubView(null); }}>
                        <Icon name="check" />
                    </button>
                </div>
            </header>
            <div className="content-area">
                <div className="section-title" style={{ paddingTop: 8 }}>Реквизиты счета</div>
                <div className="ios-group">
                    <div className="form-field">
                        <input
                            placeholder="IBAN (Например, KZ...)"
                            value={profileDraft.company_iic}
                            onChange={(e) => {
                                const val = e.target.value;
                                const info = getBankByIIK(val);
                                setProfileDraft(c => ({
                                    ...c,
                                    company_iic: val,
                                    company_bic: info ? info.bik : c.company_bic,
                                    beneficiary_bank: info ? info.name : c.beneficiary_bank
                                }));
                            }}
                        />
                    </div>
                    <div className="form-field"><input placeholder="БИК банка" value={profileDraft.company_bic} onChange={(e) => setProfileDraft((c) => ({ ...c, company_bic: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Название банка" value={profileDraft.beneficiary_bank} onChange={(e) => setProfileDraft((c) => ({ ...c, beneficiary_bank: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Кбе" value={profileDraft.company_kbe} onChange={(e) => setProfileDraft((c) => ({ ...c, company_kbe: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Код назначения платежа (КНП)" value={profileDraft.payment_code} onChange={(e) => setProfileDraft((c) => ({ ...c, payment_code: e.target.value }))} inputMode="numeric" /></div>
                </div>
                <div className="section-title">Состояние</div>
                <div className="ios-group">
                    <div className="toggle-row">
                        <span className="toggle-row-label">Сделать основным</span>
                        <Toggle checked={true} onChange={() => { }} />
                    </div>
                </div>
                <div className="form-hint">Этот счет будет использоваться по умолчанию для всех новых счетов-фактур.</div>
                {profile.company_iic && (
                    <div style={{ padding: "24px 16px 8px" }}>
                        <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteBankAccount}>
                            Удалить счет
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
