import React from "react";
import { Icon } from "../components/Common";
import { ClientRow } from "../components/ClientRow";
import type { Client, ClientBalance } from "../types";

interface ClientsViewProps {
    clients: Client[];
    clientSearch: string;
    setClientSearch: (val: string) => void;
    setSubView: (v: any) => void;
    setSelectedCatalogClient: (c: Client | null) => void;
    setClientDraft: (c: Client) => void;
    loadClientBalance: (id: number) => void;
}

export function ClientsView({
    clients,
    clientSearch,
    setClientSearch,
    setSubView,
    setSelectedCatalogClient,
    setClientDraft,
    loadClientBalance
}: ClientsViewProps) {
    const filteredClientsList = clients.filter((c) => !clientSearch || c.name.toLowerCase().includes(clientSearch.toLowerCase()) || c.bin_iin.includes(clientSearch));

    return (
        <>
            <div className="nav-bar">
                <div className="nav-bar-inner">
                    <h1 className="nav-bar-title">Клиенты</h1>
                    <button className="nav-bar-btn" onClick={() => setSubView("addClient")}><Icon name="add" /></button>
                </div>
            </div>
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
                                <ClientRow key={client.id} client={client} onClick={(cl) => {
                                    setSelectedCatalogClient(cl);
                                    setClientDraft({ ...cl, accounts: cl.accounts || [], contacts: cl.contacts || [] });
                                    loadClientBalance(cl.id);
                                    setSubView("addClient");
                                }} />
                            ))}
                        </div>
                        <div className="spacer-24" />
                    </>
                )}
            </div>
        </>
    );
}
