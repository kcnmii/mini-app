import React from "react";
import { CatalogItem } from "../types";
import { formatMoney } from "../utils";
import { Icon } from "./Common";

interface ItemRowProps {
    item: CatalogItem;
    onClick: (item: CatalogItem) => void;
}

export function ItemRow({ item, onClick }: ItemRowProps) {
    return (
        <div className="doc-row clickable" onClick={() => onClick(item)}>
            <div className="doc-row-left">
                <div className="doc-row-title">{item.name}</div>
                <div className="doc-row-meta">{formatMoney(item.price)} ₸ · {item.unit}</div>
            </div>
            <div className="ios-row-right"><Icon name="chevron_right" /></div>
        </div>
    );
}
