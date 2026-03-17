import React from "react";
import { Icon } from "../components/Common";
import { formatMoney } from "../utils";
import { fetchCompanyByBin } from "../utils/binAutofill";
import type { Client, ClientBankAccount, ClientContact } from "../types";

interface AddClientViewProps {
    tab: string;
    setSubView: (v: any) => void;
    selectedCatalogClient: Client | null;
    setSelectedCatalogClient: (c: Client | null) => void;
    createClient: () => void;
    clientBalance: any;
    clientDraft: Client;
    setClientDraft: React.Dispatch<React.SetStateAction<Client>>;
    setIsBinLoading: (v: boolean) => void;
    isBinLoading: boolean;
    setStatus: (msg: string) => void;
    clients: Client[];
    openAddClientBa: (idx?: number) => void;
    openAddClientContact: (idx?: number) => void;
    deleteClient: () => void;
    busy: string;
}

export function AddClientView({
    tab,
    setSubView,
    selectedCatalogClient,
    setSelectedCatalogClient,
    createClient,
    clientBalance,
    clientDraft,
    setClientDraft,
    setIsBinLoading,
    isBinLoading,
    setStatus,
    clients,
    openAddClientBa,
    openAddClientContact,
    deleteClient,
    busy
}: AddClientViewProps) {
    return (
        <>
            <header className="nav-bar">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => { setSubView(tab === "home" ? "invoiceForm" : null); setSelectedCatalogClient(null); }}>
                        <Icon name="close" />
                    </button>
                    <span className="nav-bar-title-center">{selectedCatalogClient ? "Клиент" : "Новый клиент"}</span>
                    <button className="nav-bar-btn-circle" onClick={createClient}>
                        <Icon name="check" />
                    </button>
                </div>
            </header>
            <div className="content-area">
                {selectedCatalogClient && clientBalance && (
                    <div style={{ padding: "16px 16px 8px" }}>
                        <div style={{ background: "rgba(0,123,255,0.05)", borderRadius: "12px", padding: "16px", border: "1px solid rgba(0,123,255,0.1)" }}>
                            <div style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "8px" }}>Баланс взаиморасчётов</div>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                                <span style={{ fontSize: "15px" }}>Выставлено:</span>
                                <span style={{ fontSize: "15px", fontWeight: 600 }}>{formatMoney(clientBalance.total_invoiced)} ₸</span>
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", color: "#34C759" }}>
                                <span style={{ fontSize: "15px" }}>Оплачено:</span>
                                <span style={{ fontSize: "15px", fontWeight: 600 }}>{formatMoney(clientBalance.total_paid)} ₸</span>
                            </div>
                            <div style={{ borderTop: "1px solid rgba(0,123,255,0.1)", margin: "8px 0" }} />
                            <div style={{ display: "flex", justifyContent: "space-between", color: clientBalance.debt > 0 ? "#FF3B30" : "inherit" }}>
                                <span style={{ fontSize: "15px", fontWeight: 600 }}>Долг:</span>
                                <span style={{ fontSize: "17px", fontWeight: 700 }}>{formatMoney(clientBalance.debt)} ₸</span>
                            </div>
                        </div>
                    </div>
                )}
                <div className="section-title">Реквизиты</div>
                <div className="ios-group">
                    <div className="form-field" style={{ position: "relative" }}>
                        <input
                            placeholder="БИН/ИИН (12 цифр)"
                            value={clientDraft.bin_iin}
                            onChange={async (e) => {
                                const val = e.target.value;
                                setClientDraft((c) => ({ ...c, bin_iin: val }));

                                if (val.length === 12) {
                                    setIsBinLoading(true);
                                    try {
                                        const info = await fetchCompanyByBin(val);
                                        if (info) {
                                            setClientDraft(c => ({
                                                ...c,
                                                name: info.name || c.name,
                                                address: info.address || c.address,
                                                director: info.director || c.director,
                                                // @ts-ignore
                                                kbe: info.type === 'ИП' ? '19' : '17'
                                            }));
                                            setStatus("Данные организации получены");
                                        }
                                    } finally {
                                        setIsBinLoading(false);
                                    }
                                }

                                const found = clients.find(cl => cl.bin_iin === val.trim() && val.trim() !== "");
                                if (found) {
                                    const firstKbe = found.accounts.length > 0 ? found.accounts[0].kbe : "";
                                    // @ts-ignore
                                    setClientDraft({ ...found, kbe: firstKbe });
                                    setSelectedCatalogClient(found);
                                }
                            }}
                        />
                        {isBinLoading && (
                            <div style={{ position: "absolute", right: "12px", top: "50%", transform: "translateY(-50%)" }}>
                                <div style={{ width: "16px", height: "16px", border: "2px solid #007AFF", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                            </div>
                        )}
                    </div>
                    <div className="form-field">
                        <input placeholder="Наименование" value={clientDraft.name} onChange={(e) => setClientDraft((c) => ({ ...c, name: e.target.value }))} />
                    </div>
                    <div className="form-field">
                        <input placeholder="Адрес" value={clientDraft.address} onChange={(e) => setClientDraft((c) => ({ ...c, address: e.target.value }))} />
                    </div>
                    <div className="form-field">
                        <input placeholder="Руководитель" value={clientDraft.director} onChange={(e) => setClientDraft((c) => ({ ...c, director: e.target.value }))} />
                    </div>
                </div>

                <div className="section-title">Счета</div>
                {clientDraft.accounts.length > 0 && (
                    <div className="ios-group">
                        {clientDraft.accounts.map((acc, idx) => (
                            <div className="ios-row clickable" key={idx} onClick={() => openAddClientBa(idx)}>
                                <div className="ios-row-content">
                                    <div className="ios-row-title">{acc.bank_name || "Новый счет"}</div>
                                    <div className="ios-row-subtitle">{acc.iic || "Без номера"}{acc.is_main ? " (Основной)" : ""}</div>
                                </div>
                                <Icon name="chevron_right" className="ios-row-chevron" />
                            </div>
                        ))}
                    </div>
                )}
                <div style={{ padding: "8px 16px 16px" }}>
                    <button className="dashed-add-btn" onClick={() => openAddClientBa()}>
                        <Icon name="add_circle" /> Добавить счет
                    </button>
                </div>

                <div className="section-title">Контакты</div>
                {clientDraft.contacts.length > 0 && (
                    <div className="ios-group">
                        {clientDraft.contacts.map((con, idx) => (
                            <div className="ios-row clickable" key={idx} onClick={() => openAddClientContact(idx)}>
                                <div className="ios-row-content">
                                    <div className="ios-row-title">{con.name || "Новый контакт"}</div>
                                    <div className="ios-row-subtitle">{con.phone || "Без телефона"}</div>
                                </div>
                                <Icon name="chevron_right" className="ios-row-chevron" />
                            </div>
                        ))}
                    </div>
                )}
                <div style={{ padding: "8px 16px 16px" }}>
                    <button className="dashed-add-btn" onClick={() => openAddClientContact()}>
                        <Icon name="add_circle" /> Добавить контакт
                    </button>
                </div>

                {selectedCatalogClient && (
                    <div style={{ padding: "24px 16px 32px" }}>
                        <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteClient}>
                            Удалить клиента
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
