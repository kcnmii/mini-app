import { useState, useCallback } from "react";
import { request, parseMoney } from "../utils";
import type { CatalogItem, ItemDraft } from "../types";

export function useCatalog(setStatus: (s: string) => void, setBusy: (b: any) => void, setSubView: (v: any) => void) {
    const [items, setItems] = useState<CatalogItem[]>([]);
    const [itemDraft, setItemDraft] = useState<ItemDraft>({ name: "", unit: "шт.", price: "", sku: "" });
    const [selectedCatalogItem, setSelectedCatalogItem] = useState<CatalogItem | null>(null);

    const createItem = useCallback(async (tab: string, addRow: (item: CatalogItem) => void) => {
        if (!itemDraft.name.trim()) return;
        setBusy("save");
        try {
            const draftNameMatch = itemDraft.name.trim().toLowerCase();
            let existingItem = items.find((it) => it.name.trim().toLowerCase() === draftNameMatch);

            const isModified = selectedCatalogItem && (
                selectedCatalogItem.name !== itemDraft.name ||
                selectedCatalogItem.unit !== itemDraft.unit ||
                parseMoney(String(selectedCatalogItem.price)) !== parseMoney(itemDraft.price) ||
                (selectedCatalogItem.sku || "") !== (itemDraft.sku || "")
            );

            if (isModified && selectedCatalogItem) {
                const updated = await request<CatalogItem>(`/catalog/items/${selectedCatalogItem.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: itemDraft.name, unit: itemDraft.unit, price: parseMoney(itemDraft.price), sku: itemDraft.sku })
                });
                setItems((c) => c.map(i => i.id === updated.id ? updated : i));
                setSelectedCatalogItem(updated);
                setStatus("Товар обновлен");
                return;
            }

            if (!existingItem) {
                existingItem = await request<CatalogItem>("/catalog/items", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: itemDraft.name, unit: itemDraft.unit, price: parseMoney(itemDraft.price), sku: itemDraft.sku })
                });
                setItems((c) => [existingItem!, ...c]);
                setStatus("Товар сохранен");
            } else {
                setStatus("Товар добавлен");
            }

            if (tab === "home" || tab === "invoices") {
                addRow(existingItem);
            }

            setItemDraft({ name: "", unit: "шт.", price: "", sku: "" });
            setSelectedCatalogItem(null);
            setSubView((tab === "home" || tab === "invoices") ? "invoiceForm" : null);
        } catch (e) {
            setStatus(e instanceof Error ? e.message : "Ошибка");
        } finally {
            setBusy("idle");
        }
    }, [itemDraft, selectedCatalogItem, items, setBusy, setStatus, setSubView]);

    const deleteItem = useCallback(async () => {
        if (!selectedCatalogItem) return;
        if (!confirm("Вы уверены, что хотите удалить этот товар/услугу?")) return;
        const deletedId = selectedCatalogItem.id;
        const backup = items;
        setItems((c) => c.filter(i => i.id !== deletedId));
        setStatus("Товар удален");
        setSubView(null);
        setSelectedCatalogItem(null);
        setItemDraft({ name: "", unit: "шт.", price: "", sku: "" });
        request(`/catalog/items/${deletedId}`, { method: "DELETE" })
            .catch(() => { setItems(backup); setStatus("Ошибка: не удалось удалить товар"); });
    }, [selectedCatalogItem, items, setStatus, setSubView]);

    return { items, setItems, itemDraft, setItemDraft, selectedCatalogItem, setSelectedCatalogItem, createItem, deleteItem };
}
