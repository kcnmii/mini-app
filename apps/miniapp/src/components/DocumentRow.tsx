import React from "react";
import { DocumentRecord } from "../types";
import { Icon } from "./Common";

interface DocumentRowProps {
    document: DocumentRecord;
    onClick: (id: number) => void;
}

export function DocumentRow({ document, onClick }: DocumentRowProps) {
    return (
        <div className="doc-row clickable" onClick={() => onClick(document.id)}>
            <div className="doc-row-left">
                <div className="doc-row-title">
                    {document.title.replace(/^Счет\s*(№|N)?\s*/i, "")} {document.client_name}
                </div>
                <div className="doc-row-meta">
                    <span className="doc-row-date">
                        {new Date(document.created_at).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}
                    </span>
                </div>
            </div>
            <div className="ios-row-right"><Icon name="chevron_right" /></div>
        </div>
    );
}
