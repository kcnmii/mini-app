import { useState, useCallback, useEffect } from "react";
import { Icon } from "./Common";
import { API_BASE_URL, request, getAuthToken } from "../utils";

interface ImageUploadRowProps {
    label: string;
    hint: string;
    imageType: "logo" | "signature" | "stamp";
    onStatusChange: (msg: string) => void;
    onSuccess?: () => void;
}

export function ImageUploadRow({ label, hint, imageType, onStatusChange, onSuccess }: ImageUploadRowProps) {
    const [preview, setPreview] = useState<string>("");

    const loadPreview = useCallback(async () => {
        try {
            const res = await request<{ has_image: boolean; data: string }>(`/profile/${imageType}/preview`);
            setPreview(res.has_image ? res.data : "");
        } catch { setPreview(""); }
    }, [imageType]);

    useEffect(() => { loadPreview(); }, [loadPreview]);

    async function handleUpload(file: File) {
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
            await loadPreview();
            onStatusChange(`${label} загружен`);
            if (onSuccess) onSuccess();
        } catch { onStatusChange(`Ошибка загрузки: ${label}`); }
    }

    return (
        <label className="upload-row">
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
            <input
                type="file"
                className="hidden-input"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }}
            />
        </label>
    );
}
