import { Client } from "../types";
import { Icon, Checkbox } from "./Common";

interface ClientRowProps {
    client: Client;
    onClick: (client: Client) => void;
    isEditMode?: boolean;
    isSelected?: boolean;
    onSelect?: (id: number) => void;
}

export function ClientRow({ client, onClick, isEditMode, isSelected, onSelect }: ClientRowProps) {
    const handleRowClick = () => {
        if (isEditMode && onSelect) {
            onSelect(client.id);
        } else {
            onClick(client);
        }
    };

    return (
        <div className={`selectable-row-container${isEditMode ? " edit-mode" : ""}`} onClick={handleRowClick}>
            <div className="selectable-checkbox-wrap">
                <Checkbox checked={!!isSelected} onChange={() => {}} />
            </div>
            <div className="doc-row clickable" style={{ flex: 1 }}>
                <div className="doc-row-left">
                    <div className="doc-row-title">{client.name}</div>
                    <div className="doc-row-meta" style={{ marginTop: "2px" }}>{client.bin_iin || "БИН не указан"}</div>
                </div>
                {!isEditMode && <div className="ios-row-right"><Icon name="chevron_right" /></div>}
            </div>
        </div>
    );
}
