import { useState, useCallback } from "react";
import { request } from "../utils";
import type { Client, ClientDraft, ClientBalance, ClientBankAccount, ClientContact } from "../types";

export function useClients(setStatus: (s: string) => void, setBusy: (b: any) => void, setSubView: (v: any) => void) {
    const [clients, setClients] = useState<Client[]>([]);
    const [clientDraft, setClientDraft] = useState<ClientDraft>({ name: "", bin_iin: "", address: "", director: "", accounts: [], contacts: [], kbe: "" });
    const [selectedCatalogClient, setSelectedCatalogClient] = useState<Client | null>(null);
    const [clientBalance, setClientBalance] = useState<ClientBalance | null>(null);

    const [clientBaDraft, setClientBaDraft] = useState<ClientBankAccount>({ iic: "", bank_name: "", bic: "", kbe: "", is_main: false });
    const [clientContactDraft, setClientContactDraft] = useState<ClientContact>({ name: "", phone: "", email: "" });
    const [editingBaIndex, setEditingBaIndex] = useState<number | null>(null);
    const [editingContactIndex, setEditingContactIndex] = useState<number | null>(null);

    const openAddClientBa = useCallback((index?: number) => {
        if (index !== undefined) {
            setClientBaDraft(clientDraft.accounts[index]);
            setEditingBaIndex(index);
        } else {
            setClientBaDraft({ iic: "", bank_name: "", bic: "", kbe: clientDraft.kbe || "", is_main: false });
            setEditingBaIndex(null);
        }
        setSubView("addClientBankAccount");
    }, [clientDraft.accounts, clientDraft.kbe, setSubView]);

    const saveClientBa = useCallback(() => {
        setClientDraft((c) => {
            const na = [...c.accounts];
            if (editingBaIndex !== null) na[editingBaIndex] = clientBaDraft;
            else na.push(clientBaDraft);
            return { ...c, accounts: na };
        });
        setSubView("addClient");
    }, [clientBaDraft, editingBaIndex, setSubView]);

    const openAddClientContact = useCallback((index?: number) => {
        if (index !== undefined) {
            setClientContactDraft(clientDraft.contacts[index]);
            setEditingContactIndex(index);
        } else {
            setClientContactDraft({ name: "", phone: "", email: "" });
            setEditingContactIndex(null);
        }
        setSubView("addClientContact");
    }, [clientDraft.contacts, setSubView]);

    const saveClientContact = useCallback(() => {
        setClientDraft((c) => {
            const nc = [...c.contacts];
            if (editingContactIndex !== null) nc[editingContactIndex] = clientContactDraft;
            else nc.push(clientContactDraft);
            return { ...c, contacts: nc };
        });
        setSubView("addClient");
    }, [clientContactDraft, editingContactIndex, setSubView]);

    const createClient = useCallback(async (tab: string, selectClient: (cl: Client) => void) => {
        if (!clientDraft.name.trim()) return;
        setBusy("save");

        if (selectedCatalogClient) {
            const optimisticClient = { ...selectedCatalogClient, ...clientDraft } as Client;
            setClients((c) => c.map(cl => cl.id === optimisticClient.id ? optimisticClient : cl));
            setStatus("Клиент обновлен");
            setSubView((tab === "home" || tab === "invoices") ? "invoiceForm" : null);
            setBusy("idle");
            request<Client>(`/clients/${selectedCatalogClient.id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(clientDraft)
            }).then(updated => {
                setClients((c) => c.map(cl => cl.id === updated.id ? updated : cl));
            }).catch(() => setStatus("Ошибка синхронизации"));
            return;
        }

        const existingByBin = clients.find(cl => cl.bin_iin === clientDraft.bin_iin && cl.bin_iin !== "");
        let finalClient: Client;

        if (!existingByBin) {
            const tempClient: Client = { id: -Date.now(), ...clientDraft, created_at: new Date().toISOString() };
            setClients((c) => [tempClient, ...c]);
            finalClient = tempClient;
            setStatus("Клиент сохранен");
            request<Client>("/clients", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(clientDraft) })
                .then(real => setClients((c) => c.map(cl => cl.id === tempClient.id ? real : cl)))
                .catch(() => {
                    setClients((c) => c.filter(cl => cl.id !== tempClient.id));
                    setStatus("Ошибка сохранения клиента");
                });
        } else {
            finalClient = existingByBin;
            setStatus("Клиент добавлен");
        }

        setClientDraft({ name: "", bin_iin: "", address: "", director: "", accounts: [], contacts: [], kbe: "" });
        setSelectedCatalogClient(null);

        if (tab === "home" || tab === "invoices") {
            selectClient(finalClient);
        }

        setSubView((tab === "home" || tab === "invoices") ? "invoiceForm" : null);
        setBusy("idle");
    }, [clientDraft, selectedCatalogClient, clients, setBusy, setStatus, setSubView]);

    const deleteClient = useCallback(async () => {
        if (!selectedCatalogClient) return;
        if (!confirm("Вы уверены, что хотите удалить этого клиента?")) return;
        const deletedId = selectedCatalogClient.id;
        const backup = clients;
        setClients((c) => c.filter(cl => cl.id !== deletedId));
        setStatus("Клиент удален");
        setSubView(null);
        setSelectedCatalogClient(null);
        setClientDraft({ name: "", bin_iin: "", address: "", director: "", accounts: [], contacts: [], kbe: "" });
        request(`/clients/${deletedId}`, { method: "DELETE" })
            .catch(() => { setClients(backup); setStatus("Ошибка: не удалось удалить клиента"); });
    }, [selectedCatalogClient, clients, setStatus, setSubView]);

    const loadClientBalance = useCallback(async (clientId: number) => {
        try {
            const b = await request<ClientBalance>(`/clients/${clientId}/balance`);
            setClientBalance(b);
        } catch (e) {
            console.error("balance fetch error", e);
        }
    }, []);

    return {
        clients, setClients, clientDraft, setClientDraft, selectedCatalogClient, setSelectedCatalogClient, clientBalance, setClientBalance,
        clientBaDraft, setClientBaDraft, clientContactDraft, setClientContactDraft, editingBaIndex, editingContactIndex,
        openAddClientBa, saveClientBa, openAddClientContact, saveClientContact,
        createClient, deleteClient, loadClientBalance
    };
}

