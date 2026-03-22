import { CatalogItem } from "../types";
import { formatMoney } from "../utils";
import { Icon, Checkbox } from "./Common";

interface ItemRowProps {
    item: CatalogItem;
    onClick: (item: CatalogItem) => void;
    isEditMode?: boolean;
    isSelected?: boolean;
    onSelect?: (id: number) => void;
}

export function ItemRow({ item, onClick, isEditMode, isSelected, onSelect }: ItemRowProps) {
    const handleRowClick = () => {
        if (isEditMode && onSelect) {
            onSelect(item.id);
        } else {
            onClick(item);
        }
    };

    return (
        <div className={`selectable-row-container${isEditMode ? " edit-mode" : ""}`} onClick={handleRowClick}>
            <div className="selectable-checkbox-wrap">
                <Checkbox checked={!!isSelected} onChange={() => {}} />
            </div>
            <div className="doc-row clickable" style={{ flex: 1 }}>
                <div className="doc-row-left">
                    <div className="doc-row-title">{item.name}</div>
                    <div className="doc-row-meta" style={{ marginTop: "2px" }}>{formatMoney(item.price)} ₸ · {item.unit}</div>
                </div>
                {!isEditMode && <div className="ios-row-right"><Icon name="chevron_right" /></div>}
            </div>
        </div>
    );
}
