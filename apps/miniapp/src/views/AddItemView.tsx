import React from "react";
import { Icon } from "../components/Common";
import { formatMoney } from "../utils";
import type { CatalogItem } from "../types";

interface AddItemViewProps {
    itemDraft: Partial<CatalogItem>;
    setItemDraft: React.Dispatch<React.SetStateAction<Partial<CatalogItem>>>;
    items: CatalogItem[];
    selectedCatalogItem: CatalogItem | null;
    setSelectedCatalogItem: (item: CatalogItem | null) => void;
    setSubView: (v: any) => void;
    createItem: () => void;
    deleteItem: () => void;
    busy: string;
    tab: string;
    animationType?: "none" | "left" | "up";
}

export function AddItemView({
    itemDraft,
    setItemDraft,
    items,
    selectedCatalogItem,
    setSelectedCatalogItem,
    setSubView,
    createItem,
    deleteItem,
    busy,
    tab,
    animationType = "left"
}: AddItemViewProps) {
    const animClass = animationType === "none" ? "" : animationType === "left" ? "animate-slide-left" : "animate-slide-up";
    return (
        <>
            <header className={`nav-bar ${animClass}`}>
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => { setSubView(tab === "home" ? "invoiceForm" : null); setSelectedCatalogItem(null); }}>
                        <Icon name={selectedCatalogItem ? "chevron_left" : "close"} />
                    </button>
                    <span className="nav-bar-title-center">{selectedCatalogItem ? "Товар/Услуга" : "Добавить товар"}</span>
                    <button className="nav-bar-btn-circle" onClick={createItem}>
                        <Icon name="check" />
                    </button>
                </div>
            </header>
            <div className={`content-area ${animClass}`}>
                <div className="ios-group" style={{ marginTop: 16 }}>
                    <div className="form-field">
                        <input
                            placeholder="Название (поиск или новое)"
                            value={itemDraft.name || ""}
                            onChange={(e) => setItemDraft((c) => ({ ...c, name: e.target.value }))}
                        />
                    </div>
                    {itemDraft.name && !items.find(i => i.name.toLowerCase() === itemDraft.name!.trim().toLowerCase()) && items.filter(i => i.name.toLowerCase().includes(itemDraft.name!.toLowerCase())).length > 0 && (
                        <>
                            {items.filter(i => i.name.toLowerCase().includes(itemDraft.name!.toLowerCase())).slice(0, 4).map(it => (
                                <div className="ios-row" key={it.id} onClick={() => {
                                    setItemDraft({ name: it.name, unit: it.unit, price: String(it.price) as any, sku: it.sku || "" });
                                    setSelectedCatalogItem(it);
                                }} style={{ cursor: "pointer", background: "rgba(0,123,255,0.05)" }}>
                                    <div className="ios-row-content">
                                        <div className="ios-row-title">{it.name}</div>
                                        <div className="ios-row-subtitle">{formatMoney(it.price)} ₸ / {it.unit}</div>
                                    </div>
                                </div>
                            ))}
                        </>
                    )}
                    <div className="form-field"><input placeholder="Ед. изм. (час, шт., кг)" value={itemDraft.unit || ""} onChange={(e) => setItemDraft((c) => ({ ...c, unit: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Цена (50 000)" type="number" value={itemDraft.price || ""} onChange={(e) => setItemDraft((c) => ({ ...c, price: e.target.value as any }))} /></div>
                    <div className="form-field"><input placeholder="Артикул (001)" value={itemDraft.sku || ""} onChange={(e) => setItemDraft((c) => ({ ...c, sku: e.target.value }))} /></div>
                </div>
                {selectedCatalogItem && (
                    <div style={{ padding: "24px 16px 8px" }}>
                        <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteItem}>
                            Удалить товар/услугу
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
