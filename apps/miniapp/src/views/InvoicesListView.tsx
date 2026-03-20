import React from "react";
import { Icon } from "../components/Common";
import { NavBar } from "../components/NavBar";
import { InvoiceRow } from "../components/InvoiceRow";
import { DocumentRow } from "../components/DocumentRow";
import type { InvoiceRecord, DocumentRecord } from "../types";

const statusFilters = ["all", "sent", "overdue", "paid", "draft"] as const;
const statusFilterLabels: Record<string, string> = { all: "Все", sent: "Отправленные", overdue: "Просроченные", paid: "Оплаченные", draft: "Черновики" };

interface InvoicesListViewProps {
    invoiceRecords: InvoiceRecord[];
    documents: DocumentRecord[];
    docSearch: string;
    setDocSearch: (val: string) => void;
    invoiceStatusFilter: string;
    setInvoiceStatusFilter: (val: string) => void;
    openNewInvoice: () => void;
    loadAndPreviewNewInvoice: (id: number) => void;
    loadAndPreviewOldDocument: (id: number) => void;
}

export function InvoicesListView({
    invoiceRecords,
    documents,
    docSearch,
    setDocSearch,
    invoiceStatusFilter,
    setInvoiceStatusFilter,
    openNewInvoice,
    loadAndPreviewNewInvoice,
    loadAndPreviewOldDocument
}: InvoicesListViewProps) {
    const filteredInvoices = invoiceRecords.filter((inv) => {
        if (invoiceStatusFilter !== "all" && inv.status !== invoiceStatusFilter) return false;
        if (docSearch && !inv.number.toLowerCase().includes(docSearch.toLowerCase()) && !inv.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
        return true;
    });

    // Fallback to old documents if no new invoices
    const filteredDocs = documents.filter((d) => {
        if (docSearch && !d.title.toLowerCase().includes(docSearch.toLowerCase()) && !d.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
        return true;
    });

    const showNewInvoicesList = invoiceRecords.length > 0;

    return (
        <>
            <NavBar title="Документы" onAction={openNewInvoice} actionIcon="add" />
            <div className="search-bar">
                <div className="search-input-wrap">
                    <Icon name="search" />
                    <input placeholder="Поиск..." value={docSearch} onChange={(e) => setDocSearch(e.target.value)} />
                </div>
            </div>
            {showNewInvoicesList && (
                <div className="status-chips-scroll">
                    {statusFilters.map((sf) => (
                        <button
                            key={sf}
                            onClick={() => setInvoiceStatusFilter(sf)}
                            className={`status-chip${invoiceStatusFilter === sf ? " active" : ""}`}
                        >
                            {statusFilterLabels[sf]}
                        </button>
                    ))}
                </div>
            )}
            <div className="content-area-scroll">
                {showNewInvoicesList ? (
                    filteredInvoices.length === 0 ? (
                        <div className="empty-state full-height">
                            <div className="empty-state-icon"><Icon name="receipt_long" /></div>
                            <div className="empty-state-title">Ничего не найдено</div>
                            <div className="empty-state-text">Нет счетов с таким статусом</div>
                        </div>
                    ) : (
                        <>
                            <div className="spacer-8" />
                            <div className="ios-group">
                                {filteredInvoices.map((inv) => (
                                    <InvoiceRow key={inv.id} invoice={inv} onClick={loadAndPreviewNewInvoice} />
                                ))}
                            </div>
                            <div className="spacer-24" />
                        </>
                    )
                ) : filteredDocs.length === 0 ? (
                    <div className="empty-state full-height">
                        <div className="empty-state-icon"><Icon name="article" /></div>
                        <div className="empty-state-title">Список пуст</div>
                        <div className="empty-state-text">Создайте свой первый счёт</div>
                    </div>
                ) : (
                    <>
                        <div className="spacer-8" />
                        <div className="ios-group">
                            {filteredDocs.map((doc) => (
                                <DocumentRow key={doc.id} document={doc} onClick={loadAndPreviewOldDocument} />
                            ))}
                        </div>
                        <div className="spacer-24" />
                    </>
                )}
            </div>
        </>
    );
}
