import React, { useState } from "react";
import { Icon, ActionSheet } from "../components/Common";
import { NavBar } from "../components/NavBar";
import { ItemRow } from "../components/ItemRow";
import type { CatalogItem } from "../types";
import { request } from "../utils";

interface ItemsViewProps {
    items: CatalogItem[];
    setItems: React.Dispatch<React.SetStateAction<CatalogItem[]>>;
    itemSearch: string;
    setItemSearch: (val: string) => void;
    setSubView: (v: any) => void;
    setSelectedCatalogItem: (i: CatalogItem | null) => void;
    setItemDraft: (draft: { name: string; unit: string; price: string; sku: string }) => void;
    setStatus: (s: string) => void;
}

export function ItemsView({
    items,
    setItems,
    itemSearch,
    setItemSearch,
    setSubView,
    setSelectedCatalogItem,
    setItemDraft,
    setStatus
}: ItemsViewProps) {
    const [isEditMode, setIsEditMode] = useState(false);
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [isActionSheetOpen, setIsActionSheetOpen] = useState(false);

    const headerRef = React.useRef<HTMLDivElement>(null);
    const inputRef = React.useRef<HTMLDivElement>(null);

    const toggleSelect = (id: number) => {
        setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    React.useEffect(() => {
        const handleScroll = () => {
            const offset = Math.max(0, window.scrollY);
            const scale = Math.min(1, Math.max(0, 1 - offset / 50));
            
            if (headerRef.current) {
                headerRef.current.style.height = `${44 * scale}px`;
                headerRef.current.style.opacity = `${scale}`;
                headerRef.current.style.transform = `scaleY(${scale})`;
                headerRef.current.style.marginBottom = `${8 * scale}px`;
                headerRef.current.style.pointerEvents = scale < 0.2 ? "none" : "auto";
            }
            if (inputRef.current) {
                inputRef.current.style.opacity = `${scale * scale}`;
                inputRef.current.style.transform = `scale(${0.9 + 0.1 * scale})`;
            }
        };
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    const handleBulkDelete = async () => {
        if (selectedIds.length === 0) return;
        setStatus(`Удаление ${selectedIds.length} позиций...`);
        const toDelete = [...selectedIds];
        setSelectedIds([]);
        setIsEditMode(false);

        try {
            await Promise.all(toDelete.map(id => request(`/catalog/items/${id}`, { method: "DELETE" })));
            setItems(prev => prev.filter(i => !toDelete.includes(i.id)));
            setStatus(`Удалено: ${toDelete.length}`);
        } catch (e) {
            setStatus("Ошибка при удалении некоторых позиций");
        }
    };

    const filteredItemsList = items.filter((i) => !itemSearch || i.name.toLowerCase().includes(itemSearch.toLowerCase()));

    return (
        <>
            <NavBar 
                title="Каталог"
                titleCenter={true}
                leftAction={
                    <button className="nav-bar-btn-circle" onClick={() => { setIsEditMode(!isEditMode); setSelectedIds([]); }}>
                        <Icon name={isEditMode ? "close" : "edit"} />
                    </button>
                }
                onAction={isEditMode ? () => setIsActionSheetOpen(true) : () => {
                    setSelectedCatalogItem(null);
                    setItemDraft({ name: "", unit: "шт.", price: "", sku: "" } as any);
                    setSubView("addItem");
                }}
                actionIcon={isEditMode ? "delete" : "add"}
            />
            
            <div className="search-header-anim" ref={headerRef} style={{ 
                height: "44px", 
                overflow: "hidden",
                transformOrigin: "top"
            }}>
                <div className="search-bar" style={{ padding: "0 16px" }}>
                    <div className="search-input-wrap" ref={inputRef} style={{ 
                        height: "36px"
                    }}>
                        <Icon name="search" />
                        <input placeholder="Поиск..." value={itemSearch} onChange={(e) => setItemSearch(e.target.value)} />
                    </div>
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
                                <ItemRow 
                                    key={item.id} 
                                    item={item} 
                                    onClick={(it) => {
                                        setSelectedCatalogItem(it);
                                        setItemDraft({ name: it.name, unit: it.unit, price: String(it.price), sku: it.sku || "" });
                                        setSubView("addItem");
                                    }} 
                                    isEditMode={isEditMode}
                                    isSelected={selectedIds.includes(item.id)}
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
                title={`Удалить ${selectedIds.length} позиций?`}
                actions={[
                    { label: "Удалить выбранное", danger: true, bold: true, onClick: handleBulkDelete }
                ]}
            />
        </>
    );
}
