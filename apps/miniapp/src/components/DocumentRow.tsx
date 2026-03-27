import { DocumentRecord } from "../types";
import { Icon, Checkbox } from "./Common";

interface DocumentRowProps {
    document: DocumentRecord;
    onClick: (id: number) => void;
    isEditMode?: boolean;
    isSelected?: boolean;
    onSelect?: (id: number) => void;
}

const getDocTypeInfo = (title: string): { code: string; label: string; color: string; bg: string } => {
    if (title.startsWith("Акт")) return { code: "АВР", label: title, color: "#34C759", bg: "rgba(52, 199, 89, 0.12)" };
    if (title.startsWith("Накладная")) return { code: "НКЛ", label: title, color: "#FF9500", bg: "rgba(255, 149, 0, 0.12)" };
    return { code: "СФ", label: title.replace(/^Счет\s*(№|N)?\s*/i, ""), color: "var(--primary, #007AFF)", bg: "rgba(0, 122, 255, 0.12)" };
};

export function DocumentRow({ document, onClick, isEditMode, isSelected, onSelect }: DocumentRowProps) {
    const handleRowClick = () => {
        if (isEditMode && onSelect) {
            onSelect(document.id);
        } else {
            onClick(document.id);
        }
    };

    const typeInfo = getDocTypeInfo(document.title);

    return (
        <div className={`selectable-row-container${isEditMode ? " edit-mode" : ""}`} onClick={handleRowClick}>
            <div className="selectable-checkbox-wrap">
                <Checkbox checked={!!isSelected} onChange={() => {}} />
            </div>
            <div className="doc-row clickable" style={{ flex: 1 }}>
                <div className="doc-row-left">
                    <div className="doc-row-title">
                        {typeInfo.label} {document.client_name && `· ${document.client_name}`}
                    </div>
                    <div className="doc-row-meta" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ background: typeInfo.bg, color: typeInfo.color, padding: "2px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 700, letterSpacing: "0.3px" }}>
                            {typeInfo.code}
                        </span>
                        {document.total_sum && (
                            <span className="doc-row-date">{document.total_sum} ₸</span>
                        )}
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
