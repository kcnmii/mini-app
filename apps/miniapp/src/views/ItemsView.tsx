import React from "react";
import { Icon } from "../components/Common";
import { ItemRow } from "../components/ItemRow";
import type { CatalogItem } from "../types";

interface ItemsViewProps {
    items: CatalogItem[];
    itemSearch: string;
    setItemSearch: (val: string) => void;
    setSubView: (v: any) => void;
    setSelectedCatalogItem: (i: CatalogItem | null) => void;
    setItemDraft: (draft: { name: string; unit: string; price: string; sku: string }) => void;
}

export function ItemsView({
    items,
    itemSearch,
    setItemSearch,
    setSubView,
    setSelectedCatalogItem,
    setItemDraft
}: ItemsViewProps) {
    const filteredItemsList = items.filter((i) => !itemSearch || i.name.toLowerCase().includes(itemSearch.toLowerCase()));

    return (
        <>
            <div className="nav-bar">
                <div className="nav-bar-inner">
                    <h1 className="nav-bar-title">Каталог</h1>
                    <button className="nav-bar-btn-circle" onClick={() => {
                        setSelectedCatalogItem(null);
                        setItemDraft({ name: "", unit: "", price: "", sku: "" } as any);
                        setSubView("addItem");
                    }}><Icon name="add" /></button>
                </div>
            </div>
            <div className="search-bar">
                <div className="search-input-wrap">
                    <Icon name="search" />
                    <input placeholder="Поиск..." value={itemSearch} onChange={(e) => setItemSearch(e.target.value)} />
                </div>
            </div>
            <div className="content-area">
                {filteredItemsList.length === 0 ? (
                    <div className="empty-state full-height">
                        <div className="empty-state-icon"><Icon name="inventory_2" /></div>
                        <div className="empty-state-title">Каталог пуст</div>
                        <div className="empty-state-text">Добавьте товары или услуги для автоматического расчета</div>
                    </div>
                ) : (
                    <>
                        <div className="spacer-8" />
                        <div className="ios-group">
                            {filteredItemsList.map((item) => (
                                <ItemRow key={item.id} item={item} onClick={(it) => {
                                    setSelectedCatalogItem(it);
                                    setItemDraft({ name: it.name, unit: it.unit, price: String(it.price), sku: it.sku || "" });
                                    setSubView("addItem");
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
