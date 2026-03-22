import { DocumentRecord } from "../types";
import { Icon, Checkbox } from "./Common";

interface DocumentRowProps {
    document: DocumentRecord;
    onClick: (id: number) => void;
    isEditMode?: boolean;
    isSelected?: boolean;
    onSelect?: (id: number) => void;
}

export function DocumentRow({ document, onClick, isEditMode, isSelected, onSelect }: DocumentRowProps) {
    const handleRowClick = () => {
        if (isEditMode && onSelect) {
            onSelect(document.id);
        } else {
            onClick(document.id);
        }
    };

    return (
        <div className={`selectable-row-container${isEditMode ? " edit-mode" : ""}`} onClick={handleRowClick}>
            <div className="selectable-checkbox-wrap">
                <Checkbox checked={!!isSelected} onChange={() => {}} />
            </div>
            <div className="doc-row clickable" style={{ flex: 1 }}>
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
                {!isEditMode && <div className="ios-row-right"><Icon name="chevron_right" /></div>}
            </div>
        </div>
    );
}
