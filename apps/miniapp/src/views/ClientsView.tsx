import React, { useState } from "react";
import { Icon, ActionSheet } from "../components/Common";
import { NavBar } from "../components/NavBar";
import { ClientRow } from "../components/ClientRow";
import type { Client } from "../types";
import { request } from "../utils";

interface ClientsViewProps {
    clients: Client[];
    setClients: React.Dispatch<React.SetStateAction<Client[]>>;
    clientSearch: string;
    setClientSearch: (val: string) => void;
    setSubView: (v: any) => void;
    setSelectedCatalogClient: (c: Client | null) => void;
    setClientDraft: (c: Client) => void;
    loadClientBalance: (id: number) => void;
    setStatus: (s: string) => void;
}

export function ClientsView({
    clients,
    setClients,
    clientSearch,
    setClientSearch,
    setSubView,
    setSelectedCatalogClient,
    setClientDraft,
    loadClientBalance,
    setStatus
}: ClientsViewProps) {
    const [isEditMode, setIsEditMode] = useState(false);
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [isActionSheetOpen, setIsActionSheetOpen] = useState(false);

    const toggleSelect = (id: number) => {
        setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    const handleBulkDelete = async () => {
        if (selectedIds.length === 0) return;
        setStatus(`Удаление ${selectedIds.length} клиентов...`);
        const toDelete = [...selectedIds];
        setSelectedIds([]);
        setIsEditMode(false);

        try {
            await Promise.all(toDelete.map(id => request(`/clients/${id}`, { method: "DELETE" })));
            setClients(prev => prev.filter(c => !toDelete.includes(c.id)));
            setStatus(`Удалено: ${toDelete.length}`);
        } catch (e) {
            setStatus("Ошибка при удалении некоторых клиентов");
        }
    };

    const filteredClientsList = clients.filter((c) => !clientSearch || c.name.toLowerCase().includes(clientSearch.toLowerCase()) || c.bin_iin.includes(clientSearch));

    return (
        <>
            <NavBar 
                title="Клиенты"
                titleCenter={true}
                leftAction={
                    <button className="nav-bar-btn-circle" onClick={() => { setIsEditMode(!isEditMode); setSelectedIds([]); }}>
                        <Icon name={isEditMode ? "close" : "edit"} />
                    </button>
                }
                onAction={isEditMode ? () => setIsActionSheetOpen(true) : () => {
                    setSelectedCatalogClient(null);
                    setClientDraft({ name: "", bin_iin: "", address: "", director: "", accounts: [], contacts: [] } as any);
                    setSubView("addClient");
                }}
                actionIcon={isEditMode ? "delete" : "add"}
            />
            <div className="search-bar">
                <div className="search-input-wrap">
                    <Icon name="search" />
                    <input placeholder="Поиск..." value={clientSearch} onChange={(e) => setClientSearch(e.target.value)} />
                </div>
            </div>
            <div className="content-area">
                {filteredClientsList.length === 0 ? (
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
                                    isSelected={selectedIds.includes(client.id)}
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
                title={`Удалить ${selectedIds.length} клиентов?`}
                actions={[
                    { label: "Удалить выбранное", danger: true, bold: true, onClick: handleBulkDelete }
                ]}
            />
        </>
    );
}
