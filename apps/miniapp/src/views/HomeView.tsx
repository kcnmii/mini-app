import React from "react";
import { Icon } from "../components/Common";
import { Dashboard } from "../components/Dashboard";
import { InvoiceRow } from "../components/InvoiceRow";
import { DocumentRow } from "../components/DocumentRow";
import type { DashboardSummary, InvoiceRecord, DocumentRecord, SupplierProfileData, BankAccount } from "../types";

interface HomeViewProps {
    bankAccounts: BankAccount[];
    selectedBankAccountId: number | null;
    profile: SupplierProfileData;
    dashboardSummary: DashboardSummary;
    invoiceRecords: InvoiceRecord[];
    documents: DocumentRecord[];

    fileInputRef: React.RefObject<HTMLInputElement | null>;

    setProfileDraft: (p: SupplierProfileData) => void;
    setSubView: (v: any) => void;
    setTab: (t: any) => void;
    openNewInvoice: () => void;
    handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
    loadAndPreviewNewInvoice: (id: number) => void;
    loadAndPreviewOldDocument: (id: number) => void;
}

export function HomeView({
    bankAccounts,
    selectedBankAccountId,
    profile,
    dashboardSummary,
    invoiceRecords,
    documents,
    fileInputRef,
    setProfileDraft,
    setSubView,
    setTab,
    openNewInvoice,
    handleFileUpload,
    loadAndPreviewNewInvoice,
    loadAndPreviewOldDocument
}: HomeViewProps) {
    const selectedBa = bankAccounts.find(b => b.id === selectedBankAccountId);
    const bankBtnLabel = bankAccounts.length === 0 ? "Добавить счёт" : selectedBa ? selectedBa.bank_name : "Все счета";

    return (
        <>
            <div className="nav-bar">
                <div className="nav-bar-inner">
                    <button className="nav-bar-btn-circle" onClick={() => {
                        if (bankAccounts.length === 0) { setProfileDraft(profile); setSubView("addBankAccount"); }
                        else setSubView("bankPicker");
                    }} style={{ borderRadius: "20px", width: "auto", padding: "0 14px", gap: "6px", fontSize: "14px", fontWeight: 600 }}>
                        <Icon name={bankAccounts.length === 0 ? "add" : "account_balance"} />
                        <span>{bankBtnLabel}</span>
                    </button>
                    <button className="nav-bar-btn-circle" onClick={() => setSubView("dateFilter")}>
                        <Icon name="calendar_month" />
                    </button>
                </div>
            </div>
            <div className="content-area">
                <Dashboard summary={dashboardSummary} />

                {/* ── Create invoice & Import 1C buttons ── */}
                <div style={{ padding: "16px 16px 0", display: "flex", flexDirection: "column", gap: "10px" }}>
                    <button className="home-action-btn home-action-btn--primary" onClick={openNewInvoice}>
                        <Icon name="add_circle" /> Выставить счёт
                    </button>
                    <button className="home-action-btn home-action-btn--secondary" onClick={() => fileInputRef.current?.click()}>
                        <Icon name="upload" /> Загрузить выписку
                    </button>
                    <input type="file" ref={fileInputRef} onChange={handleFileUpload} accept=".txt" style={{ display: 'none' }} />
                </div>

                {/* ── Recent invoices ── */}
                {invoiceRecords.length > 0 ? (
                    <>
                        <div className="section-header-row" style={{ padding: "20px 16px 8px" }}>
                            <h2 style={{ textTransform: "none", fontSize: "18px", fontWeight: 600, color: "var(--text)", letterSpacing: "normal", margin: 0 }}>Последние</h2>
                            <button className="nav-bar-pill-btn" style={{ fontSize: "14px", height: "36px", padding: "0 12px 0 16px" }} onClick={() => setTab("invoices")}>
                                Все <Icon name="chevron_right" />
                            </button>
                        </div>
                        <div className="ios-group" style={{ margin: "0 16px" }}>
                            {invoiceRecords.slice(0, 10).map((inv) => (
                                <InvoiceRow key={inv.id} invoice={inv} onClick={loadAndPreviewNewInvoice} showDate={false} />
                            ))}
                        </div>
                    </>
                ) : documents.length > 0 ? (
                    <>
                        <div className="section-header-row" style={{ padding: "20px 16px 8px" }}>
                            <h2 style={{ textTransform: "none", fontSize: "18px", fontWeight: 600, color: "var(--text)", letterSpacing: "normal", margin: 0 }}>Последние документы</h2>
                        </div>
                        <div className="ios-group" style={{ margin: "0 16px" }}>
                            {documents.slice(0, 10).map((doc) => (
                                <DocumentRow key={doc.id} document={doc} onClick={loadAndPreviewOldDocument} />
                            ))}
                        </div>
                    </>
                ) : (
                    <div className="empty-state" style={{ marginTop: 24 }}>
                        <div className="empty-state-icon"><Icon name="receipt_long" /></div>
                        <div className="empty-state-title">Нет счетов</div>
                        <div className="empty-state-text">Создайте первый счёт, чтобы начать контролировать деньги</div>
                    </div>
                )}
                <div className="spacer-24" />
            </div>
        </>
    );
}
