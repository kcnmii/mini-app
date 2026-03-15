import React from "react";
import { Client } from "../types";
import { Icon } from "./Common";

interface ClientRowProps {
    client: Client;
    onClick: (client: Client) => void;
}

export function ClientRow({ client, onClick }: ClientRowProps) {
    return (
        <div className="doc-row clickable" onClick={() => onClick(client)}>
            <div className="doc-row-left">
                <div className="doc-row-title">{client.name}</div>
                <div className="doc-row-meta">{client.bin_iin || "БИН не указан"}</div>
            </div>
            <div className="ios-row-right"><Icon name="chevron_right" /></div>
        </div>
    );
}
