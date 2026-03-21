import React from "react";
import { Icon } from "../components/Common";
import type { Client, ClientContact } from "../types";

interface AddClientContactViewProps {
    setSubView: (v: any) => void;
    clientContactDraft: ClientContact;
    setClientContactDraft: React.Dispatch<React.SetStateAction<ClientContact>>;
    saveClientContact: () => void;
    editingContactIndex: number | null;
    setClientDraft: React.Dispatch<React.SetStateAction<Client>>;
}

export function AddClientContactView({
    setSubView,
    clientContactDraft,
    setClientContactDraft,
    saveClientContact,
    editingContactIndex,
    setClientDraft
}: AddClientContactViewProps) {
    return (
        <>
            <header className="nav-bar animate-slide-up">
                <div className="nav-bar-detail">
                    <button className="nav-bar-btn-circle" onClick={() => setSubView("addClient")}>
                        <Icon name={editingContactIndex !== null ? "chevron_left" : "close"} />
                    </button>
                    <span className="nav-bar-title-center">Контакт</span>
                    <button className="nav-bar-btn-circle" onClick={saveClientContact}>
                        <Icon name="check" />
                    </button>
                </div>
            </header>
            <div className="content-area animate-slide-up">
                <div className="ios-group" style={{ marginTop: 16 }}>
                    <div className="form-field"><input placeholder="Имя" value={clientContactDraft.name} onChange={(e) => setClientContactDraft(c => ({ ...c, name: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Телефон" value={clientContactDraft.phone} onChange={(e) => setClientContactDraft(c => ({ ...c, phone: e.target.value }))} /></div>
                    <div className="form-field"><input placeholder="Email" value={clientContactDraft.email} onChange={(e) => setClientContactDraft(c => ({ ...c, email: e.target.value }))} /></div>
                </div>
                {editingContactIndex !== null && (
                    <div style={{ padding: "16px" }}>
                        <button className="destructive-btn" onClick={() => {
                            setClientDraft((c: Client) => ({ ...c, contacts: c.contacts.filter((_, i) => i !== editingContactIndex) }));
                            setSubView("addClient");
                        }}>Удалить контакт</button>
                    </div>
                )}
            </div>
        </>
    );
}
