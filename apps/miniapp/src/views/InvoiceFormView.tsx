import React from "react";
import { Icon, Toggle } from "../components/Common";
import { formatMoney, parseMoney } from "../utils";
import type { Client, CatalogItem, InvoiceForm, DocumentRecord, InvoiceRecord, SupplierProfileData } from "../types";

interface InvoiceFormViewProps {
    invoice: InvoiceForm;
    setInvoice: React.Dispatch<React.SetStateAction<InvoiceForm>>;
    setSubView: (v: any) => void;
    selectedDocId: number | null;
    selectedInvoiceId: number | null;
    saveInvoice: () => void;
    busy: string;
    invoiceClientSearch: string;
    setInvoiceClientSearch: (v: string) => void;
    filteredClients: Client[];
    selectClient: (cl: Client) => void;
    bankAccounts: any[];
    changeQuantity: (idx: number, delta: number) => void;
    removeRow: (idx: number) => void;
    deleteInvoice: () => void;
    profile: SupplierProfileData;
    sendInvoice: () => void;
    animationType?: "none" | "left" | "up";
    openAddItem: () => void;
}

export function InvoiceFormView({
    invoice,
    setInvoice,
    setSubView,
    selectedDocId,
    selectedInvoiceId,
    saveInvoice,
    busy,
    invoiceClientSearch,
    setInvoiceClientSearch,
    filteredClients,
    selectClient,
    bankAccounts,
    changeQuantity,
    removeRow,
    deleteInvoice,
    profile,
    sendInvoice,
    animationType = "left",
    openAddItem
}: InvoiceFormViewProps) {
    const animClass = animationType === "none" ? "" : animationType === "left" ? "animate-slide-left" : "animate-slide-up";
    const statusLabels: Record<string, string> = { draft: "Черновик", sent: "Отправлен", paid: "Оплачен", overdue: "Просрочен" };

    return (
        <>
            <div className={`nav-bar ${animClass}`}>

                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => (selectedDocId || selectedInvoiceId) ? setSubView("viewDocument") : setSubView(null)}>
                        <Icon name={(selectedDocId || selectedInvoiceId) ? "chevron_left" : "close"} />
                    </button>
                    <span className="nav-bar-title-center">{(selectedDocId || selectedInvoiceId) ? `Счет ${invoice.INVOICE_NUMBER}` : "Новый счет"}</span>
                    <div className="nav-bar-right">
                        <button className="nav-bar-btn-circle" onClick={saveInvoice} disabled={busy !== "idle"}>
                            <Icon name="check" />
                        </button>
                    </div>
                </div>
            </div>
            <div className={`content-area has-footer ${animClass}`}>
                <div className="section-title" style={{ paddingTop: 8 }}>Даты</div>
                <div className="ios-group">
                    <div className="form-field">
                        <span className="form-field-label">Дата счета</span>
                        <input
                            type="date"
                            className="native-date-input"
                            value={invoice.INVOICE_DATE.includes('.') ? invoice.INVOICE_DATE.split('.').reverse().join('-') : invoice.INVOICE_DATE}
                            onChange={(e) => {
                                const val = e.target.value;
                                const [y, m, d] = val.split('-');
                                setInvoice((c) => ({ ...c, INVOICE_DATE: (y && m && d) ? `${d}.${m}.${y}` : val }));
                            }}
                        />
                    </div>
                    <div className="field-divider" />
                    <div className="form-field">
                        <span className="form-field-label">Срок оплаты</span>
                        <input
                            type="date"
                            className="native-date-input"
                            value={invoice.DUE_DATE || ""}
                            onChange={(e) => setInvoice(c => ({ ...c, DUE_DATE: e.target.value }))}
                        />
                    </div>
                </div>
                {bankAccounts.length > 0 && (
                    <>
                        <div className="section-title">Банковский счёт</div>
                        <div className="ios-group">
                            {bankAccounts.map(ba => (
                                <button className="ios-row" key={ba.id} onClick={() => {
                                    setInvoice(c => ({
                                        ...c,
                                        COMPANY_IIC: ba.account_number,
                                        COMPANY_BIC: ba.bic,
                                        BENEFICIARY_BANK: ba.bank_name,
                                    }));
                                }}>
                                    <div className="ios-row-content">
                                        <div className="ios-row-title">{ba.bank_name || ba.account_number}</div>
                                        <div className="ios-row-subtitle" style={{ textTransform: "uppercase" }}>{ba.account_number}</div>
                                    </div>
                                    {invoice.COMPANY_IIC === ba.account_number && <Icon name="check" style={{ color: "var(--primary)" }} />}
                                </button>
                            ))}
                        </div>
                    </>
                )}
                <div className="section-title">Клиент и договор</div>
                <div className="ios-group">
                    <div className="form-field">
                        <span className="form-field-icon"><Icon name="search" /></span>
                        <input placeholder="Поиск по имени или БИН" value={invoiceClientSearch} onChange={(e) => setInvoiceClientSearch(e.target.value)} onClick={() => { if (invoiceClientSearch === invoice.CLIENT_NAME) setInvoiceClientSearch("") }} />
                    </div>
                    {(invoiceClientSearch && invoiceClientSearch !== invoice.CLIENT_NAME) && filteredClients.length > 0 && (
                        <>
                            {filteredClients.slice(0, 4).map((cl) => (
                                <div className="ios-row" key={cl.id} onClick={() => selectClient(cl)} style={{ cursor: "pointer" }}>
                                    <div className="ios-row-content">
                                        <div className="ios-row-title">{cl.name}</div>
                                        <div className="ios-row-subtitle">{cl.bin_iin}</div>
                                    </div>
                                </div>
                            ))}
                        </>
                    )}
                    <div className="field-divider" />
                    <div className="form-field">
                        <span className="form-field-icon"><Icon name="contract" /></span>
                        <input placeholder="Договор (опционально)..." value={invoice.DEAL_REFERENCE || ""} onChange={(e) => setInvoice(c => ({ ...c, DEAL_REFERENCE: e.target.value }))} />
                    </div>
                    <div className="field-divider" />
                    <div className="form-field">
                        <span className="form-field-icon"><Icon name="payments" /></span>
                        <input
                            placeholder="Код назначения платежа (КНП)"
                            value={invoice.PAYMENT_CODE || ""}
                            onChange={(e) => setInvoice(c => ({ ...c, PAYMENT_CODE: e.target.value }))}
                            inputMode="numeric"
                        />
                    </div>
                </div>
                <div className="section-title">Позиции</div>
                {invoice.items.length > 0 && (
                    <div className="ios-group">
                        {invoice.items.map((it, idx) => (
                            <div className="ios-row item-row animate-fade-in-up" key={`inv-${it.number}-${idx}`}>
                                <div className="ios-row-content">
                                    <div className="ios-row-title">{it.name || "Без названия"}</div>
                                    <div className="ios-row-subtitle">
                                        {formatMoney(parseMoney(it.price))} ₸ × {it.quantity} {it.unit}
                                    </div>
                                </div>
                                <div className="ios-row-right" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                    <div className="qty-selector">
                                        <button className="qty-btn" onClick={(e) => { e.stopPropagation(); changeQuantity(idx, -1); }}><Icon name="remove" /></button>
                                        <span className="qty-value">{it.quantity}</span>
                                        <button className="qty-btn" onClick={(e) => { e.stopPropagation(); changeQuantity(idx, 1); }}><Icon name="add" /></button>
                                    </div>
                                    <span onClick={(e) => { e.stopPropagation(); removeRow(idx); }} className="item-delete-btn">
                                        <Icon name="delete" />
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
                <div style={{ padding: "12px 16px 16px" }}>
                    <button className="dashed-add-btn" onClick={openAddItem}>
                        <Icon name="add_circle" /> Добавить позицию
                    </button>
                </div>
                <div className="section-title">Настройки документа</div>
                <div className="ios-group">
                    <div className="toggle-row">
                        <div className="toggle-row-left"><Icon name="approval" /><span className="toggle-row-label">Печать</span></div>
                        <Toggle checked={invoice.INCLUDE_STAMP} disabled={!profile.stamp_path} onChange={(v) => setInvoice((c) => ({ ...c, INCLUDE_STAMP: v }))} />
                    </div>
                    <div className="toggle-row">
                        <div className="toggle-row-left"><Icon name="draw" /><span className="toggle-row-label">Подпись</span></div>
                        <Toggle checked={invoice.INCLUDE_SIGNATURE} disabled={!profile.signature_path} onChange={(v) => setInvoice((c) => ({ ...c, INCLUDE_SIGNATURE: v }))} />
                    </div>
                    <div className="toggle-row">
                        <div className="toggle-row-left"><Icon name="image" /><span className="toggle-row-label">Логотип</span></div>
                        <Toggle checked={invoice.INCLUDE_LOGO} disabled={!profile.logo_path} onChange={(v) => setInvoice((c) => ({ ...c, INCLUDE_LOGO: v }))} />
                    </div>
                </div>
                {(selectedDocId || selectedInvoiceId) && (
                    <div style={{ padding: "0 16px" }}>
                        <button className="destructive-btn" onClick={deleteInvoice} disabled={busy !== "idle"}>
                            <Icon name="delete" /> Удалить документ
                        </button>
                    </div>
                )}
                <div className="spacer-24" />
            </div>
            <div className={`invoice-footer ${animClass}`}>
                <div className="invoice-footer-inner">
                    <div className="invoice-total-row">
                        <span className="invoice-total-label">Общая сумма</span>
                        <span className="invoice-total-value">{invoice.TOTAL_SUM} ₸</span>
                    </div>
                    <button className="invoice-send-btn" disabled={busy !== "idle"} onClick={sendInvoice}>
                        <Icon name="send" />{busy === "send" ? "Отправка..." : "Отправить"}
                    </button>
                </div>
            </div>
        </>
    );
}
