import React, { useState } from "react";
import { Icon, ActionSheet } from "../components/Common";
import { NavBar } from "../components/NavBar";
import { ClientRow } from "../components/ClientRow";
import { ItemRow } from "../components/ItemRow";
import type { Client, CatalogItem } from "../types";
import { request } from "../utils";

interface DirectoryViewProps {
    clients: Client[];
    setClients: React.Dispatch<React.SetStateAction<Client[]>>;
    clientSearch: string;
    setClientSearch: (val: string) => void;
    setSelectedCatalogClient: (c: Client | null) => void;
    setClientDraft: (c: any) => void;
    loadClientBalance: (id: number) => void;

    items: CatalogItem[];
    setItems: React.Dispatch<React.SetStateAction<CatalogItem[]>>;
    itemSearch: string;
    setItemSearch: (val: string) => void;
    setSelectedCatalogItem: (i: CatalogItem | null) => void;
    setItemDraft: (draft: any) => void;

    setSubView: (v: any) => void;
    setStatus: (s: string) => void;
}

export function DirectoryView({
    clients, setClients, clientSearch, setClientSearch, setSelectedCatalogClient, setClientDraft, loadClientBalance,
    items, setItems, itemSearch, setItemSearch, setSelectedCatalogItem, setItemDraft,
    setSubView, setStatus
}: DirectoryViewProps) {
    const [activeTab, setActiveTab] = useState<"clients" | "items">("clients");
    const [isEditMode, setIsEditMode] = useState(false);
    
    // Selection state is separate for clients and items
    const [selectedClientIds, setSelectedClientIds] = useState<number[]>([]);
    const [selectedItemIds, setSelectedItemIds] = useState<number[]>([]);
    
    const [isActionSheetOpen, setIsActionSheetOpen] = useState(false);

    const toggleSelectClient = (id: number) => {
        setSelectedClientIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    const toggleSelectItem = (id: number) => {
        setSelectedItemIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    const handleBulkDelete = async () => {
        if (activeTab === "clients") {
            if (selectedClientIds.length === 0) return;
            setStatus(`Удаление ${selectedClientIds.length} клиентов...`);
            const toDelete = [...selectedClientIds];
            setSelectedClientIds([]);
            setIsEditMode(false);

            try {
                await Promise.all(toDelete.map(id => request(`/clients/${id}`, { method: "DELETE" })));
                setClients(prev => prev.filter(c => !toDelete.includes(c.id)));
                setStatus(`Удалено: ${toDelete.length}`);
            } catch (e) {
                setStatus("Ошибка при удалении клиентов");
            }
        } else {
            if (selectedItemIds.length === 0) return;
            setStatus(`Удаление ${selectedItemIds.length} позиций...`);
            const toDelete = [...selectedItemIds];
            setSelectedItemIds([]);
            setIsEditMode(false);

            try {
                await Promise.all(toDelete.map(id => request(`/catalog/items/${id}`, { method: "DELETE" })));
                setItems(prev => prev.filter(i => !toDelete.includes(i.id)));
                setStatus(`Удалено: ${toDelete.length}`);
            } catch (e) {
                setStatus("Ошибка при удалении позиций");
            }
        }
    };

    const filteredClientsList = clients.filter((c) => !clientSearch || c.name.toLowerCase().includes(clientSearch.toLowerCase()) || c.bin_iin.includes(clientSearch));
    const filteredItemsList = items.filter((i) => !itemSearch || i.name.toLowerCase().includes(itemSearch.toLowerCase()));

    const selectedCount = activeTab === "clients" ? selectedClientIds.length : selectedItemIds.length;

    return (
        <>
            <NavBar 
                title="Справочник"
                titleCenter={true}
                leftAction={
                    <button className="nav-bar-btn-circle" onClick={() => { 
                        setIsEditMode(!isEditMode); 
                        if (activeTab === "clients") setSelectedClientIds([]);
                        else setSelectedItemIds([]);
                    }}>
                        <Icon name={isEditMode ? "close" : "edit"} />
                    </button>
                }
                onAction={isEditMode ? () => setIsActionSheetOpen(true) : () => {
                    if (activeTab === "clients") {
                        setSelectedCatalogClient(null);
                        setClientDraft({ name: "", bin_iin: "", address: "", director: "", accounts: [], contacts: [] } as any);
                        setSubView("addClient");
                    } else {
                        setSelectedCatalogItem(null);
                        setItemDraft({ name: "", unit: "шт.", price: "", sku: "" } as any);
                        setSubView("addItem");
                    }
                }}
                actionIcon={isEditMode ? "delete" : "add"}
            />

            <div className="search-header-anim" style={{ height: "auto" }}>
                <div className="segmented-control">
                    <div className="segmented-control-inner">
                        <button 
                            className={`segment-btn ${activeTab === "clients" ? "active" : ""}`}
                            onClick={() => { setActiveTab("clients"); setIsEditMode(false); }}
                        >
                            Клиенты
                        </button>
                        <button 
                            className={`segment-btn ${activeTab === "items" ? "active" : ""}`}
                            onClick={() => { setActiveTab("items"); setIsEditMode(false); }}
                        >
                            Склад
                        </button>
                    </div>
                </div>

                <div className="search-bar" style={{ padding: "0 16px" }}>
                    <div className="search-input-wrap" style={{ height: "36px" }}>
                        <Icon name="search" />
                        <input 
                            placeholder={activeTab === "clients" ? "Поиск клиентов..." : "Поиск товаров..."} 
                            value={activeTab === "clients" ? clientSearch : itemSearch} 
                            onChange={(e) => activeTab === "clients" ? setClientSearch(e.target.value) : setItemSearch(e.target.value)} 
                        />
                    </div>
                </div>
            </div>

            <div className="content-area">
                {activeTab === "clients" ? (
                    filteredClientsList.length === 0 ? (
                        <div className="empty-state full-height">
                            <div className="empty-state-icon"><Icon name="group" /></div>
                            <div className="empty-state-title">База клиентов пуста</div>
                            <div className="empty-state-text">Добавьте клиентов, чтобы быстрее оформлять документы</div>
                        </div>
                    ) : (
                        <>
                            <div className="spacer-8" />
                            <div className="ios-group">
                                {filteredClientsList.map((client) => (
                                    <ClientRow 
                                        key={client.id} 
                                        client={client} 
                                        onClick={(cl) => {
                                            setSelectedCatalogClient(cl);
                                            setClientDraft({ ...cl, accounts: cl.accounts || [], contacts: cl.contacts || [] });
                                            loadClientBalance(cl.id);
                                            setSubView("addClient");
                                        }} 
                                        isEditMode={isEditMode}
                                        isSelected={selectedClientIds.includes(client.id)}
                                        onSelect={toggleSelectClient}
                                    />
                                ))}
                            </div>
                            <div className="spacer-24" />
                        </>
                    )
                ) : (
                    filteredItemsList.length === 0 ? (
                        <div className="empty-state full-height">
                            <div className="empty-state-icon"><Icon name="inventory_2" /></div>
                            <div className="empty-state-title">Склад пуст</div>
                            <div className="empty-state-text">Добавьте товары или услуги</div>
                        </div>
                    ) : (
                        <>
                            <div className="spacer-8" />
                            <div className="ios-group">
                                {filteredItemsList.map((item) => (
                                    <ItemRow 
                                        key={item.id} 
                                        item={item} 
                                        onClick={(it) => {
                                            setSelectedCatalogItem(it);
                                            setItemDraft({ name: it.name, unit: it.unit, price: String(it.price), sku: it.sku || "" });
                                            setSubView("addItem");
                                        }} 
                                        isEditMode={isEditMode}
                                        isSelected={selectedItemIds.includes(item.id)}
                                        onSelect={toggleSelectItem}
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
                title={`Удалить ${selectedCount} ${activeTab === "clients" ? "клиентов" : "позиций"}?`}
                actions={[
                    { label: "Удалить выбранное", danger: true, bold: true, onClick: handleBulkDelete }
                ]}
            />
        </>
    );
}
