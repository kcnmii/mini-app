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
    const [scrollOffset, setScrollOffset] = useState(0);

    const toggleSelect = (id: number) => {
        setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    React.useEffect(() => {
        const handleScroll = () => {
            // Clamp scrollY to 0 to avoid stretches during overscroll on iOS
            const offset = Math.max(0, window.scrollY);
            if (offset < 100) {
                setScrollOffset(offset);
            } else {
                setScrollOffset(100);
            }
        };
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    // Calculate animation values based on scroll (strictly clamped 0 to 1)
    const searchScale = Math.min(1, Math.max(0, 1 - scrollOffset / 50));
    const searchHeight = 44 * searchScale;
    const chipsOpacity = Math.min(1, Math.max(0, 1 - (scrollOffset - 20) / 40));

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
                    <button className="nav-bar-btn-circle" onClick={() => { setIsEditMode(!isEditMode); setSelectedIds([]); }}>
                        <Icon name={isEditMode ? "close" : "edit"} />
                    </button>
                }
                onAction={isEditMode ? () => setIsActionSheetOpen(true) : openNewInvoice} 
                actionIcon={isEditMode ? "delete" : "add"} 
            />
            
            <div className="search-header-anim" style={{ 
                height: `${searchHeight}px`, 
                opacity: searchScale,
                overflow: "hidden",
                transform: `scaleY(${searchScale})`,
                transformOrigin: "top",
                marginBottom: `${Math.max(0, 8 * searchScale)}px`,
                pointerEvents: searchScale < 0.2 ? "none" : "auto"
            }}>
                <div className="search-bar" style={{ padding: "0 16px" }}>
                    <div className="search-input-wrap" style={{ 
                        opacity: searchScale * searchScale,
                        height: "36px",
                        transform: `scale(${0.9 + 0.1 * searchScale})`
                    }}>
                        <Icon name="search" />
                        <input placeholder="Поиск..." value={docSearch} onChange={(e) => setDocSearch(e.target.value)} />
                    </div>
                </div>
            </div>

            {showNewInvoicesList && (
                <div className="status-chips-scroll" style={{ 
                    opacity: chipsOpacity,
                    transform: `translateY(${(1 - chipsOpacity) * -15}px)`,
                    pointerEvents: chipsOpacity < 0.1 ? "none" : "auto",
                    display: chipsOpacity === 0 ? "none" : "flex"
                }}>
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
        </>
    );
}
