import React, { useState } from "react";
import { Icon } from "../components/Common";
import { Toggle } from "../components/Common";
import { ImageUploadRow } from "../components/ImageUploadRow";
import type { SupplierProfileData, TelegramWebApp } from "../types";

// Quick copy of getAvatarColor from utils (or we should import it)
// We'll import it from App.tsx's parent context or utils
import { getAvatarColor } from "../utils";

interface ProfileViewProps {
    tgUser: any;
    tgName: string;
    profile: SupplierProfileData;
    bankAccounts: any[];
    webAppInitData: boolean;
    setProfileDraft: (p: SupplierProfileData) => void;
    setSubView: (v: any) => void;
    setStatus: (msg: string) => void;
    refreshProfileImages: () => void;
    deleteBankAccount: (id: number) => void;
    toggleNotifications: (enabled: boolean) => void;
    onLogout: () => void;
}

export function ProfileView({
    tgUser,
    tgName,
    profile,
    bankAccounts,
    webAppInitData,
    setProfileDraft,
    setSubView,
    setStatus,
    refreshProfileImages,
    deleteBankAccount,
    toggleNotifications,
    onLogout
}: ProfileViewProps) {
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const savedTheme = localStorage.getItem("theme");
    const [isDarkTheme, setIsDarkTheme] = useState(savedTheme === "dark" || (savedTheme !== "light" && prefersDark));

    const toggleTheme = () => {
        const nextIsDark = !isDarkTheme;
        setIsDarkTheme(nextIsDark);
        localStorage.setItem("theme", nextIsDark ? "dark" : "light");
        if (nextIsDark) document.documentElement.setAttribute("data-theme", "dark");
        else document.documentElement.setAttribute("data-theme", "light");
    };

    return (
        <div className="content-area">
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "24px 16px 16px" }}>
                <div className="user-avatar" style={{
                    width: "80px", height: "80px",
                    background: tgUser?.photo_url ? "transparent" : getAvatarColor(tgName),
                    color: "white", fontSize: "32px", fontWeight: 700,
                    marginBottom: "12px"
                }}>
                    {tgUser?.photo_url ? (
                        <img src={tgUser.photo_url} alt="avatar" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
                    ) : (
                        tgName.charAt(0).toUpperCase()
                    )}
                </div>
                <h1 style={{ fontSize: "22px", fontWeight: 700, margin: "0 0 4px" }}>{tgName}</h1>
                {tgUser?.username && <span style={{ fontSize: "15px", color: "var(--text-secondary)" }}>@{tgUser.username}</span>}
            </div>
            <div className="section-title" style={{ paddingTop: 8 }}>Реквизиты</div>
            {profile.company_name ? (
                <div className="ios-group">
                    <div className="ios-row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                            <span style={{ fontSize: 15, fontWeight: 600 }}>{profile.company_name}</span>
                            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>БИН: {profile.company_iin}</span>
                            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Директор: {profile.executor_name}</span>
                        </div>
                        <button className="requisites-card-edit" onClick={() => { setProfileDraft(profile); setSubView("editRequisites"); }}><Icon name="edit" /></button>
                    </div>
                </div>
            ) : (
                <div style={{ padding: "0 16px", marginBottom: 20 }}>
                    <button className="dashed-add-btn" onClick={() => { setProfileDraft(profile); setSubView("editRequisites"); }}>
                        <Icon name="add_circle" /> Добавить реквизиты
                    </button>
                </div>
            )}
            <div className="section-title">Банковские счета</div>
            <div className="ios-group">
                {bankAccounts.length === 0 && (
                    <div style={{ padding: "12px 16px", textAlign: "center", color: "var(--text-secondary)", fontSize: 14 }}>
                        Счета не добавлены
                    </div>
                )}
                {bankAccounts.map(ba => (
                    <div className="ios-row" key={ba.id} style={{ justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                            <span style={{ fontSize: 14, fontWeight: 600 }}>{ba.bank_name || "Без названия"}</span>
                            <span style={{ fontSize: 13, color: "var(--text-secondary)", fontVariantNumeric: "tabular-nums" }}>{ba.account_number}</span>
                            {ba.account_number === profile.company_iic && <div><span className="badge badge-blue">Основной</span></div>}
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                            <button className="requisites-card-edit" style={{ background: "rgba(255, 59, 48, 0.1)", color: "#ff3b30", width: 32, height: 32, borderRadius: 16 }} onClick={() => deleteBankAccount(ba.id)}>
                                <Icon name="delete" />
                            </button>
                        </div>
                    </div>
                ))}
            </div>
            <div style={{ padding: "12px 16px 20px" }}>
                <button className="dashed-add-btn" onClick={() => { setProfileDraft(profile); setSubView("addBankAccount"); }}>
                    <Icon name="add_circle" /> Добавить счет
                </button>
            </div>
            <div className="section-title">Оформление документов</div>
            <div className="ios-group">
                <ImageUploadRow label="Логотип" hint="PNG или JPG, макс. 2МБ" imageType="logo" onStatusChange={setStatus} onSuccess={refreshProfileImages} />
                <ImageUploadRow label="Подпись" hint="На прозрачном фоне" imageType="signature" onStatusChange={setStatus} onSuccess={refreshProfileImages} />
                <ImageUploadRow label="Печать" hint="Круглая печать организации" imageType="stamp" onStatusChange={setStatus} onSuccess={refreshProfileImages} />
            </div>
            <div className="section-title">Общие настройки</div>
            <div className="ios-group">
                <div className="settings-row">
                    <div className="settings-row-left">
                        <div className="settings-icon red"><Icon name="notifications" filled /></div>
                        <span className="settings-row-label">Уведомления</span>
                    </div>
                    <Toggle checked={profile.notifications_enabled} onChange={(v) => toggleNotifications(v)} />
                </div>
                <div className="settings-row">
                    <div className="settings-row-left">
                        <div className="settings-icon blue"><Icon name="language" /></div>
                        <span className="settings-row-label">Язык</span>
                    </div>
                    <div className="settings-row-right"><span>Русский</span><Icon name="chevron_right" /></div>
                </div>
                <div className="settings-row" onClick={toggleTheme} style={{ cursor: "pointer" }}>
                    <div className="settings-row-left">
                        <div className="settings-icon dark"><Icon name="dark_mode" /></div>
                        <span className="settings-row-label">Тёмная тема</span>
                    </div>
                    <div style={{ pointerEvents: "none" }}>
                        <Toggle checked={isDarkTheme} onChange={() => {}} />
                    </div>
                </div>
            </div>
            {!webAppInitData && (
                <div style={{ marginTop: "16px", padding: "0 16px" }}>
                    <button onClick={onLogout} style={{ background: "var(--tg-theme-destructive-text-color, #ff3b30)", color: "white", width: "100%", padding: "14px", borderRadius: "12px", fontSize: "16px", fontWeight: 600, border: "none" }}>Выйти</button>
                </div>
            )}
            <div className="version-text">Версия приложения 1.0.0</div>
        </div>
    );
}
