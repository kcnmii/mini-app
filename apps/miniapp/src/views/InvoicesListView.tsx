import React, { useState } from "react";
import { Icon, ActionSheet } from "../components/Common";
import { NavBar } from "../components/NavBar";
import { InvoiceRow } from "../components/InvoiceRow";
import { DocumentRow } from "../components/DocumentRow";
import type { InvoiceRecord, DocumentRecord } from "../types";
import { request } from "../utils";

const statusFilters = ["all", "sent", "overdue", "paid", "draft"] as const;
const statusFilterLabels: Record<string, string> = { all: "Все", sent: "Отправленные", overdue: "Просроченные", paid: "Оплаченные", draft: "Черновики" };

interface InvoicesListViewProps {
    invoiceRecords: InvoiceRecord[];
    setInvoiceRecords: React.Dispatch<React.SetStateAction<InvoiceRecord[]>>;
    documents: DocumentRecord[];
    setDocuments: React.Dispatch<React.SetStateAction<DocumentRecord[]>>;
    docSearch: string;
    setDocSearch: (val: string) => void;
    invoiceStatusFilter: string;
    setInvoiceStatusFilter: (val: string) => void;
    openNewInvoice: () => void;
    loadAndPreviewNewInvoice: (id: number) => void;
    loadAndPreviewOldDocument: (id: number) => void;
    setStatus: (s: string) => void;
}

export function InvoicesListView({
    invoiceRecords,
    setInvoiceRecords,
    documents,
    setDocuments,
    docSearch,
    setDocSearch,
    invoiceStatusFilter,
    setInvoiceStatusFilter,
    openNewInvoice,
    loadAndPreviewNewInvoice,
    loadAndPreviewOldDocument,
    setStatus
}: InvoicesListViewProps) {
    const [isEditMode, setIsEditMode] = useState(false);
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [isActionSheetOpen, setIsActionSheetOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<"outgoing" | "incoming">("outgoing");

    const [showCreateMenu, setShowCreateMenu] = useState(false);
    const [isClosingCreateMenu, setIsClosingCreateMenu] = useState(false);

    const closeCreateMenu = () => {
        setIsClosingCreateMenu(true);
        setTimeout(() => {
            setShowCreateMenu(false);
            setIsClosingCreateMenu(false);
        }, 300);
    };

    const toggleSelect = (id: number) => {
        setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    const handleBulkDelete = async () => {
        if (selectedIds.length === 0) return;
        setStatus(`Удаление ${selectedIds.length} объектов...`);
        const toDelete = [...selectedIds];
        setSelectedIds([]);
        setIsEditMode(false);

        try {
            await Promise.all(toDelete.map(id => {
                const isInv = invoiceRecords.some(r => r.id === id);
                return request(isInv ? `/invoices/${id}` : `/documents/${id}`, { method: "DELETE" });
            }));
            setInvoiceRecords(prev => prev.filter(r => !toDelete.includes(r.id)));
            setDocuments(prev => prev.filter(r => !toDelete.includes(r.id)));
            setStatus(`Удалено: ${toDelete.length}`);
        } catch (e) {
            setStatus("Ошибка при удалении некоторых объектов");
        }
    };

    const filteredInvoices = invoiceRecords.filter((inv) => {
        if (invoiceStatusFilter !== "all" && inv.status !== invoiceStatusFilter) return false;
        if (docSearch && !inv.number.toLowerCase().includes(docSearch.toLowerCase()) && !inv.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
        return true;
    });

    const filteredDocs = documents.filter((d) => {
        if (docSearch && !d.title.toLowerCase().includes(docSearch.toLowerCase()) && !d.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
        return true;
    });

    const showNewInvoicesList = invoiceRecords.length > 0;

    return (
        <>
            <NavBar 
                title="Документы" 
                titleCenter={true}
                leftAction={
                    activeTab === "outgoing" && (
                        <button className="nav-bar-btn-circle" onClick={() => { setIsEditMode(!isEditMode); setSelectedIds([]); }}>
                            <Icon name={isEditMode ? "close" : "edit"} />
                        </button>
                    )
                }
                onAction={activeTab === "outgoing" ? (isEditMode ? () => setIsActionSheetOpen(true) : () => setShowCreateMenu(true)) : undefined}
                actionIcon={activeTab === "outgoing" ? (isEditMode ? "delete" : "add") : undefined} 
            />
            
            <div className="search-header-anim" style={{ height: "auto" }}>
                <div className="segmented-control">
                    <div className="segmented-control-inner">
                        <button 
                            className={`segment-btn ${activeTab === "outgoing" ? "active" : ""}`}
                            onClick={() => { setActiveTab("outgoing"); setIsEditMode(false); setSelectedIds([]); }}
                        >
                            Исходящие
                        </button>
                        <button 
                            className={`segment-btn ${activeTab === "incoming" ? "active" : ""}`}
                            onClick={() => { setActiveTab("incoming"); setIsEditMode(false); setSelectedIds([]); }}
                        >
                            Входящие
                        </button>
                    </div>
                </div>

                <div className="search-bar" style={{ padding: "0 16px" }}>
                    <div className="search-input-wrap" style={{ height: "36px" }}>
                        <Icon name="search" />
                        <input placeholder="Поиск..." value={docSearch} onChange={(e) => setDocSearch(e.target.value)} />
                    </div>
                </div>
            </div>

            {activeTab === "outgoing" && showNewInvoicesList && (
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




            <div className="content-area">
                {activeTab === "incoming" ? (
                    <div className="empty-state full-height">
                        <div className="empty-state-icon"><Icon name="inbox" /></div>
                        <div className="empty-state-title">Входящие документы отсутствуют</div>
                        <div className="empty-state-text">Ожидайте поступления новых документов</div>
                    </div>
                ) : (
                    showNewInvoicesList ? (
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
                                        <InvoiceRow 
                                            key={inv.id} 
                                            invoice={inv} 
                                            onClick={loadAndPreviewNewInvoice} 
                                            isEditMode={isEditMode}
                                            isSelected={selectedIds.includes(inv.id)}
                                            onSelect={toggleSelect}
                                        />
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
                                    <DocumentRow 
                                        key={doc.id} 
                                        document={doc} 
                                        onClick={loadAndPreviewOldDocument} 
                                        isEditMode={isEditMode}
                                        isSelected={selectedIds.includes(doc.id)}
                                        onSelect={toggleSelect}
                                    />
                                ))}
                            </div>
                            <div className="spacer-24" />
                        </>
                    )
                )}
            </div>

            <ActionSheet 
                isOpen={isActionSheetOpen} 
                onClose={() => setIsActionSheetOpen(false)}
                title={`Удалить ${selectedIds.length} объектов?`}
                actions={[
                    { label: "Удалить выбранное", danger: true, bold: true, onClick: handleBulkDelete }
                ]}
            />

            {(showCreateMenu || isClosingCreateMenu) && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1100, display: "flex", alignItems: "flex-end", backdropFilter: "blur(2px)", opacity: isClosingCreateMenu ? 0 : 1, transition: "opacity 0.3s ease" }} onClick={closeCreateMenu}>
                    <div className={isClosingCreateMenu ? "animate-slide-down" : "animate-slide-up"} style={{ width: "100%", background: "var(--card, #fff)", borderTopLeftRadius: "24px", borderTopRightRadius: "24px", padding: "12px 20px 32px", paddingBottom: "max(32px, env(safe-area-inset-bottom))" }} onClick={e => e.stopPropagation()}>
                        <div style={{ width: "36px", height: "5px", borderRadius: "3px", backgroundColor: "var(--separator, #C7C7CC)", margin: "0 auto 16px" }} />
                        
                        <h3 style={{ margin: "0 0 20px 0", fontSize: "20px", fontWeight: 700, color: "var(--text, #1c1c1e)", textAlign: "left" }}>Создать документ</h3>
                        
                        <div style={{ display: "flex", flexDirection: "column" }}>
                            <button
                                onClick={() => {
                                    closeCreateMenu();
                                    openNewInvoice();
                                }}
                                style={{ height: "56px", background: "none", border: "none", color: "var(--text, #1c1c1e)", fontSize: "17px", fontWeight: 500, display: "flex", alignItems: "center", gap: "16px", padding: "0", cursor: "pointer", width: "100%" }}
                            >
                                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "rgba(0, 122, 255, 0.1)", color: "var(--primary, #007AFF)", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="request_quote" style={{ fontSize: "20px" }} /></div>
                                <span>Счёт на оплату</span>
                            </button>
                            <button
                                onClick={() => {
                                    closeCreateMenu();
                                }}
                                style={{ height: "56px", background: "none", border: "none", color: "var(--text, #1c1c1e)", fontSize: "17px", fontWeight: 500, display: "flex", alignItems: "center", gap: "16px", padding: "0", cursor: "pointer", width: "100%" }}
                            >
                                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "rgba(52, 199, 89, 0.1)", color: "var(--ios-green, #34C759)", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="description" style={{ fontSize: "20px" }} /></div>
                                <span>АВР (Акт выполненных работ)</span>
                            </button>
                            <button
                                onClick={() => {
                                    closeCreateMenu();
                                }}
                                style={{ height: "56px", background: "none", border: "none", color: "var(--text, #1c1c1e)", fontSize: "17px", fontWeight: 500, display: "flex", alignItems: "center", gap: "16px", padding: "0", cursor: "pointer", width: "100%" }}
                            >
                                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "rgba(255, 149, 0, 0.1)", color: "#FF9500", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name="local_shipping" style={{ fontSize: "20px" }} /></div>
                                <span>Накладная на отпуск запасов</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
