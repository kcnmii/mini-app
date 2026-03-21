import { useState, useCallback, useEffect, useRef } from "react";
import { Icon } from "./Common";
import { API_BASE_URL, request, getAuthToken } from "../utils";

interface ImageUploadRowProps {
    label: string;
    hint: string;
    imageType: "logo" | "signature" | "stamp";
    onStatusChange: (msg: string) => void;
    onSuccess?: () => void;
}

const previewCache: Record<string, string> = {};

export function ImageUploadRow({ label, hint, imageType, onStatusChange, onSuccess }: ImageUploadRowProps) {
    const [preview, setPreview] = useState<string>(previewCache[imageType] || "");
    const [showSheet, setShowSheet] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadPreview = useCallback(async () => {
        if (previewCache[imageType]) {
            setPreview(previewCache[imageType]);
            return;
        }
        try {
            const res = await request<{ has_image: boolean; data: string }>(`/profile/${imageType}/preview`);
            const dataStr = res.has_image ? res.data : "";
            previewCache[imageType] = dataStr;
            setPreview(dataStr);
        } catch { setPreview(""); }
    }, [imageType]);

    useEffect(() => { loadPreview(); }, [loadPreview]);

    async function handleUpload(file: File) {
        setShowSheet(false);
        try {
            const fd = new FormData();
            fd.append("file", file);
            const headers: Record<string, string> = {};
            const token = getAuthToken();
            if (token) headers["Authorization"] = `Bearer ${token}`;

            await fetch(`${API_BASE_URL}/profile/${imageType}`, {
                method: "POST",
                body: fd,
                headers
            });
            delete previewCache[imageType];
            await loadPreview();
            onStatusChange(`${label} загружен`);
            if (onSuccess) onSuccess();
        } catch { onStatusChange(`Ошибка загрузки: ${label}`); }
    }

    async function handleDelete() {
        setShowSheet(false);
        try {
            await request(`/profile/${imageType}`, { method: "DELETE" });
            delete previewCache[imageType];
            setPreview("");
            onStatusChange(`${label} удален`);
            if (onSuccess) onSuccess();
        } catch { onStatusChange(`Ошибка удаления: ${label}`); }
    }

    return (
        <>
            <div className="upload-row" onClick={() => setShowSheet(true)} style={{ cursor: "pointer" }}>
                <div className="upload-row-info">
                    <span className="upload-row-title">{label}</span>
                    <span className="upload-row-hint">{hint}</span>
                </div>
                <div className="upload-row-action">
                    {preview ? (
                        <div className="upload-preview-thumb"><img src={preview} alt={label} /></div>
                    ) : (
                        <Icon name="cloud_upload" />
                    )}
                </div>
            </div>

            <input
                type="file"
                className="hidden-input"
                accept="image/png,image/jpeg,image/webp"
                ref={fileInputRef}
                onChange={(e) => { 
                    const f = e.target.files?.[0]; 
                    if (f) handleUpload(f); 
                }}
            />

            {showSheet && (
                <div className="action-sheet-overlay" onClick={() => setShowSheet(false)}>
                    <div className="action-sheet" onClick={(e) => e.stopPropagation()}>
                        <div className="action-sheet-group">
                            <button className="action-sheet-btn" onClick={() => { setShowSheet(false); fileInputRef.current?.click(); }}>
                                Загрузить фото
                            </button>
                            {preview && (
                                <button className="action-sheet-btn danger" onClick={handleDelete}>
                                    Удалить фото
                                </button>
                            )}
                        </div>
                        <div className="action-sheet-group">
                            <button className="action-sheet-btn bold" onClick={() => setShowSheet(false)}>
                                Отмена
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
