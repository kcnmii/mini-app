import React from "react";
import { Icon } from "../components/Common";
import { fetchCompanyByBin } from "../utils/binAutofill";
import type { SupplierProfileData } from "../types";

interface EditRequisitesViewProps {
    profile: SupplierProfileData;
    profileDraft: SupplierProfileData;
    setProfileDraft: React.Dispatch<React.SetStateAction<SupplierProfileData>>;
    setSubView: (v: any) => void;
    saveProfile: () => void;
    deleteRequisites: () => void;
    busy: string;
    isBinLoading: boolean;
    setIsBinLoading: (v: boolean) => void;
    setStatus: (msg: string) => void;
}

export function EditRequisitesView({
    profile,
    profileDraft,
    setProfileDraft,
    setSubView,
    saveProfile,
    deleteRequisites,
    busy,
    isBinLoading,
    setIsBinLoading,
    setStatus
}: EditRequisitesViewProps) {
    return (
        <>
            <header className="nav-bar">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">Реквизиты</span>
                    <button className="nav-bar-btn-circle" onClick={() => { saveProfile(); setSubView(null); }}>
                        <Icon name="check" />
                    </button>
                </div>
            </header>
            <div className="content-area-scroll">
                <div className="section-title" style={{ paddingTop: 8 }}>Реквизиты организации</div>
                <div className="ios-group">
                    <div className="form-field" style={{ position: "relative" }}>
                        <input
                            placeholder="БИН (12-значный номер)"
                            value={profileDraft.company_iin}
                            onChange={async (e) => {
                                const val = e.target.value;
                                setProfileDraft((c) => ({ ...c, company_iin: val, supplier_iin: val }));
                                if (val.length === 12) {
                                    setIsBinLoading(true);
                                    try {
                                        const info = await fetchCompanyByBin(val);
                                        if (info) {
                                            setProfileDraft(c => ({
                                                ...c,
                                                company_name: info.name || c.company_name,
                                                supplier_name: info.name || c.supplier_name,
                                                supplier_iin: val,
                                                supplier_address: info.address || c.supplier_address,
                                                executor_name: info.director || c.executor_name,
                                                company_kbe: info.type === 'ИП' ? '19' : '17'
                                            }));
                                            setStatus("Данные организации получены");
                                        }
                                    } finally {
                                        setIsBinLoading(false);
                                    }
                                }
                            }}
                        />
                        {isBinLoading && (
                            <div style={{ position: "absolute", right: "12px", top: "50%", transform: "translateY(-50%)" }}>
                                <div style={{ width: "16px", height: "16px", border: "2px solid #007AFF", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                            </div>
                        )}
                    </div>
                    <div className="form-field"><input placeholder="Название организации" value={profileDraft.company_name} onChange={(e) => setProfileDraft((c) => ({ ...c, company_name: e.target.value, supplier_name: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Адрес (Юридический адрес)" value={profileDraft.supplier_address} onChange={(e) => setProfileDraft((c) => ({ ...c, supplier_address: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="ФИО (например, Иванов И.И.)" value={profileDraft.executor_name} onChange={(e) => setProfileDraft((c) => ({ ...c, executor_name: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Должность (например, Директор)" value={profileDraft.position} onChange={(e) => setProfileDraft((c) => ({ ...c, position: e.target.value }))} /></div>
                </div>

                {profile.company_iin && (
                    <div style={{ padding: "24px 16px 8px" }}>
                        <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteRequisites}>
                            Удалить реквизиты
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
