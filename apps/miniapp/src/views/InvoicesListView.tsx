import React, { useState, useEffect } from "react";
import { Icon, ActionSheet } from "../components/Common";
import { NavBar } from "../components/NavBar";
import { InvoiceRow } from "../components/InvoiceRow";
import { DocumentRow } from "../components/DocumentRow";
import { EdoStatusBadge } from "../components/EdoComponents";
import type { InvoiceRecord, DocumentRecord, IncomingDocumentRecord } from "../types";
import { request, getAvatarColor } from "../utils";

import { type DocTypeFilter } from "./DocumentFilterView";

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
    loadAndPreviewDocument: (id: number) => void;
    setStatus: (s: string) => void;
    docTypeFilter: DocTypeFilter;
    setDocTypeFilter: (val: DocTypeFilter) => void;
    setSubView: (val: any) => void;
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
    loadAndPreviewDocument,
    setStatus,
    docTypeFilter,
    setDocTypeFilter,
    setSubView
}: InvoicesListViewProps) {
    const [isEditMode, setIsEditMode] = useState(false);
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [isActionSheetOpen, setIsActionSheetOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<"outgoing" | "incoming">("outgoing");

    // Incoming documents state
    const [incomingDocs, setIncomingDocs] = useState<IncomingDocumentRecord[]>([]);
    const [isLoadingIncoming, setIsLoadingIncoming] = useState(false);
    const [incomingLoaded, setIncomingLoaded] = useState(false);

    const [showCreateMenu, setShowCreateMenu] = useState(false);
    const [isClosingCreateMenu, setIsClosingCreateMenu] = useState(false);

    const closeCreateMenu = () => {
        setIsClosingCreateMenu(true);
        setTimeout(() => {
            setShowCreateMenu(false);
            setIsClosingCreateMenu(false);
        }, 300);
    };

    // Load incoming documents when tab switches
    useEffect(() => {
        if (activeTab === "incoming" && !incomingLoaded) {
            setIsLoadingIncoming(true);
            request<IncomingDocumentRecord[]>("/edo/incoming")
                .then(data => {
                    setIncomingDocs(data);
                    setIncomingLoaded(true);
                })
                .catch(err => {
                    console.error("Failed to load incoming docs:", err);
                    setStatus("Ошибка загрузки входящих");
                })
                .finally(() => setIsLoadingIncoming(false));
        }
    }, [activeTab, incomingLoaded]);

    // BACKGROUND POLLING for incoming docs status updates
    useEffect(() => {
        if (activeTab !== "incoming") return;
        
        const interval = setInterval(async () => {
             try {
                const updated = await request<IncomingDocumentRecord[]>("/edo/incoming");
                // Only update state if JSON changed to prevent flickering
                if (JSON.stringify(updated) !== JSON.stringify(incomingDocs)) {
                    setIncomingDocs(updated);
                }
             } catch (e) {
                 console.error("Background poll failed:", e);
             }
        }, 15000); // 15 seconds polling interval for list view

        return () => clearInterval(interval);
    }, [activeTab, incomingDocs]);

    const toggleSelect = (id: number) => {
        setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    const openFilters = () => {
        setSubView("documentFilter");
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

    const filteredInvoices = ["all", "invoice"].includes(docTypeFilter)
        ? invoiceRecords.filter((inv) => {
            if (invoiceStatusFilter !== "all" && inv.status !== invoiceStatusFilter) return false;
            if (docSearch && !inv.number.toLowerCase().includes(docSearch.toLowerCase()) && !inv.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
            return true;
        })
        : [];

    const nonInvoiceDocs = documents.filter((d) => {
        if (d.title.startsWith("Счет")) return false;
        
        // Filter by Type
        if (docTypeFilter === "invoice") return false;
        if (docTypeFilter === "avr" && !d.title.startsWith("Акт") && !d.title.startsWith("АВР")) return false;
        if (docTypeFilter === "waybill" && !d.title.startsWith("Накладная") && !d.title.startsWith("НКЛ")) return false;

        // If the user selects a specific Status (e.g. "Paid"), and they didn't explicitly pick a non-invoice Type,
        // it makes sense to hide non-invoices, since only invoices can be "Paid".
        if (invoiceStatusFilter !== "all" && typeof invoiceStatusFilter === "string") {
            // But if they selected "AVR", the status filter shouldn't hide it.
            if (docTypeFilter === "all") return false; 
        }

        if (docSearch && !d.title.toLowerCase().includes(docSearch.toLowerCase()) && !d.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
        return true;
    });

    // Build unified list: merge invoices + non-invoice docs, sorted by date desc
    type UnifiedItem = { type: "invoice"; data: typeof invoiceRecords[0]; date: number } | { type: "document"; data: typeof documents[0]; date: number };
    const unifiedItems: UnifiedItem[] = [
        ...filteredInvoices.map(inv => ({ type: "invoice" as const, data: inv, date: new Date(inv.created_at).getTime() })),
        ...nonInvoiceDocs.map(doc => ({ type: "document" as const, data: doc, date: new Date(doc.created_at).getTime() }))
    ].sort((a, b) => b.date - a.date);

    // Group items by local date string
    const groupedItems: Record<string, UnifiedItem[]> = {};
    unifiedItems.forEach(item => {
        const d = new Date(item.date);
        const day = d.getDate();
        const monthNames = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
        const month = monthNames[d.getMonth()];
        const key = `${day} ${month}`;
        if (!groupedItems[key]) groupedItems[key] = [];
        groupedItems[key].push(item);
    });

    const filteredDocs = documents.filter((d) => {
        if (docSearch && !d.title.toLowerCase().includes(docSearch.toLowerCase()) && !d.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
        return true;
    });

    const showNewInvoicesList = invoiceRecords.length > 0;
    const hasAnyOutgoingContent = showNewInvoicesList || nonInvoiceDocs.length > 0;

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

                <div className="search-bar" style={{ padding: "0 16px", display: "flex", gap: "10px", paddingBottom: "12px" }}>
                    <div className="search-input-wrap" style={{ height: "36px", flex: 1, borderRadius: "10px", background: "var(--card)", display: "flex", alignItems: "center", padding: "0 10px", color: "var(--text-muted, #8e8e93)" }}>
                        <Icon name="search" style={{ fontSize: "20px" }} />
                        <input placeholder="Поиск..." value={docSearch} onChange={(e) => setDocSearch(e.target.value)} style={{ border: "none", background: "transparent", outline: "none", flex: 1, height: "100%", padding: "0 8px", fontSize: "17px", color: "var(--text, #1c1c1e)" }} />
                    </div>
                    {/* The square filter button next to search */}
                    <div 
                        onClick={openFilters}
                        style={{ position: "relative", zIndex: 999, pointerEvents: "auto", height: "36px", width: "36px", borderRadius: "10px", background: "var(--card)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", cursor: "pointer", flexShrink: 0 }}
                    >
                        <Icon name="filter_list" />
                        {/* Dot indicator if filters active */}
                        {(invoiceStatusFilter !== "all" || docTypeFilter !== "all") && (
                            <div style={{ position: "absolute", top: 4, right: 4, width: 8, height: 8, borderRadius: "50%", background: "#FF3B30", border: "2px solid var(--bg, #f2f2f7)" }} />
                        )}
                    </div>
                </div>
            </div>

            <div className="content-area">
                {activeTab === "incoming" ? (
                    isLoadingIncoming ? (
                        <div className="empty-state full-height">
                            <div className="spinner" style={{ width: "28px", height: "28px", borderColor: "var(--primary, #007AFF)", borderTopColor: "transparent", borderWidth: "3px" }} />
                        </div>
                    ) : incomingDocs.length === 0 ? (
                        <div className="empty-state full-height">
                            <div className="empty-state-icon"><Icon name="inbox" /></div>
                            <div className="empty-state-title">Входящие документы отсутствуют</div>
                            <div className="empty-state-text">Когда контрагенты отправят вам документы на подписание — они появятся здесь</div>
                        </div>
                    ) : (
                        <>
                            <div style={{ height: "12px" }} />
                            <div style={{ padding: "0 16px" }}>
                                {incomingDocs.map(doc => {
                                    const typeInfo = doc.doc_type === "act" 
                                        ? { code: "АВР", color: "#34C759", bg: "rgba(52,199,89,0.12)" }
                                        : doc.doc_type === "waybill"
                                        ? { code: "НКЛ", color: "#FF9500", bg: "rgba(255,149,0,0.12)" }
                                        : doc.doc_type === "invoice"
                                        ? { code: "СЧ", color: "#AF52DE", bg: "rgba(175,82,222,0.12)" }
                                        : { code: "ДОК", color: "var(--primary, #007AFF)", bg: "rgba(0,122,255,0.12)" };
                                    
                                    const avatarColor = getAvatarColor(doc.sender_name);
                                    const initials = doc.sender_name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
                                    
                                    return (
                                        <div 
                                            key={`inc-${doc.id}`}
                                            className="doc-row clickable"
                                            onClick={() => {
                                                if (doc.share_uuid) {
                                                    // Open via share link preview
                                                    loadAndPreviewDocument(doc.id);
                                                }
                                            }}
                                            style={{ 
                                                marginBottom: "8px", 
                                                background: "var(--card, #fff)", 
                                                borderRadius: "16px", 
                                                padding: "14px 16px",
                                                display: "flex",
                                                alignItems: "center",
                                                gap: "12px",
                                            }}
                                        >
                                            {/* Sender avatar */}
                                            <div style={{
                                                width: "44px", height: "44px", borderRadius: "14px",
                                                background: `linear-gradient(135deg, ${avatarColor}22, ${avatarColor}44)`,
                                                display: "flex", alignItems: "center", justifyContent: "center",
                                                fontSize: "15px", fontWeight: 700, color: avatarColor,
                                                flexShrink: 0,
                                            }}>
                                                {initials || "?"}
                                            </div>
                                            
                                            {/* Content */}
                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                                                    <span style={{ 
                                                        fontSize: "14px", fontWeight: 600, 
                                                        color: "var(--text, #1c1c1e)",
                                                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                                                    }}>
                                                        {doc.sender_name}
                                                    </span>
                                                </div>
                                                <div style={{ 
                                                    fontSize: "13px", color: "var(--text-muted, #8e8e93)",
                                                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                                                    marginBottom: "6px",
                                                }}>
                                                    {doc.title} {doc.total_sum ? `· ${doc.total_sum} ₸` : ""}
                                                </div>
                                                <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                                                    <span style={{ 
                                                        background: typeInfo.bg, color: typeInfo.color, 
                                                        padding: "2px 8px", borderRadius: "6px", 
                                                        fontSize: "11px", fontWeight: 700 
                                                    }}>
                                                        {typeInfo.code}
                                                    </span>
                                                    <EdoStatusBadge status={doc.edo_status} style={{ padding: "2px 8px" }} />
                                                    <span style={{ fontSize: "11px", color: "var(--text-muted, #8e8e93)" }}>
                                                        {new Date(doc.created_at).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}
                                                    </span>
                                                </div>
                                            </div>
                                            
                                            {/* Arrow */}
                                            <Icon name="chevron_right" style={{ color: "var(--text-muted, #8e8e93)", fontSize: "20px", flexShrink: 0 }} />
                                        </div>
                                    );
                                })}
                            </div>
                            <div className="spacer-24" />
                        </>
                    )
                ) : (
                    !hasAnyOutgoingContent ? (
                        filteredDocs.length === 0 ? (
                            <div className="empty-state full-height">
                                <div className="empty-state-icon"><Icon name="outbox" /></div>
                                <div className="empty-state-title">Исходящие документы отсутствуют</div>
                                <div className="empty-state-text">Создайте свой первый документ, чтобы он появился в списке</div>
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
                    ) : (
                        unifiedItems.length === 0 ? (
                            <div className="empty-state full-height">
                                <div className="empty-state-icon"><Icon name="receipt_long" /></div>
                                <div className="empty-state-title">Ничего не найдено</div>
                                <div className="empty-state-text">Нет документов с таким статусом</div>
                            </div>
                        ) : (
                            <>
                                <div style={{ height: "12px" }} />
                                <div style={{ padding: "0 16px" }}>
                                    {Object.entries(groupedItems).map(([dateLabel, items]) => (
                                        <div key={dateLabel} style={{ marginBottom: "24px" }}>
                                            <div style={{ padding: "0 4px 10px", fontSize: "14px", fontWeight: 700, color: "var(--text)" }}>
                                                {dateLabel}
                                            </div>
                                            <div className="ios-group" style={{ margin: 0 }}>
                                                {items.map((item) => 
                                                    item.type === "invoice" ? (
                                                        <InvoiceRow 
                                                            key={`inv-${item.data.id}`} 
                                                            invoice={item.data as typeof invoiceRecords[0]} 
                                                            onClick={loadAndPreviewNewInvoice} 
                                                            isEditMode={isEditMode}
                                                            isSelected={selectedIds.includes(item.data.id)}
                                                            onSelect={toggleSelect}
                                                            showDate={false}
                                                        />
                                                    ) : (
                                                        <DocumentRow 
                                                            key={`doc-${item.data.id}`} 
                                                            document={item.data as typeof documents[0]} 
                                                            onClick={loadAndPreviewDocument}
                                                            isEditMode={isEditMode}
                                                            isSelected={selectedIds.includes(item.data.id)}
                                                            onSelect={toggleSelect}
                                                            showDate={false}
                                                        />
                                                    )
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="spacer-24" />
                            </>
                        )
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
