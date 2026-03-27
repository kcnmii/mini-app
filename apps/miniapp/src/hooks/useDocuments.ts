import { useState, useCallback } from "react";
import { request, makeInitialInvoice, buildInvoicePatch } from "../utils";
import type { DocumentRecord, SupplierProfileData, InvoiceForm } from "../types";

export function useDocuments(setStatus: (s: string) => void, setBusy: (b: any) => void, profile: SupplierProfileData, setSubView: (v: any) => void) {
    const [documents, setDocuments] = useState<DocumentRecord[]>([]);

    const loadAndPreviewOldDocument = useCallback(async (id: number, setInvoice: (i: any) => void, setInvoiceClientSearch: (s: string) => void) => {
        setBusy("save");
        try {
            const doc = await request<DocumentRecord & { payload_json?: string }>(`/documents/${id}`);

            if (doc.payload_json) {
                try {
                    const payload = JSON.parse(doc.payload_json);
                    setInvoice(payload);
                    setInvoiceClientSearch(payload.CLIENT_NAME || "");
                } catch (e) {
                    console.error("Parse error", e);
                }
            } else if ((doc as any).reconstructed_items) {
                const items = (doc as any).reconstructed_items.map((it: any, idx: number) => ({
                    number: idx + 1,
                    name: it.name,
                    quantity: String(it.quantity),
                    unit: it.unit,
                    price: String(it.price),
                    total: String(it.total),
                    code: it.code || ""
                }));
                const reconstructed = makeInitialInvoice(profile);
                reconstructed.CLIENT_NAME = doc.client_name;
                reconstructed.items = items;
                const numMatch = doc.title.match(/(?:№|N)\s*([^\s]+)/);
                if (numMatch) reconstructed.INVOICE_NUMBER = numMatch[1];

                // Sync with calculated totals (Items line, Sum in words, etc.)
                Object.assign(reconstructed, buildInvoicePatch(reconstructed.items));

                setInvoice(reconstructed);
                setInvoiceClientSearch(doc.client_name);
            }
            setSubView("invoiceForm");
        } catch (e) {
            setStatus("Ошибка загрузки");
        } finally {
            setBusy("idle");
        }
    }, [profile, setBusy, setStatus, setSubView]);

    const loadAndPreviewDocument = useCallback(async (id: number, setPreviewPages: (p: string[]) => void, setIsPdfLoading: (v: boolean) => void, setSelectedDocId: (id: number | null) => void, setSelectedInvoiceId: (id: number | null) => void) => {
        setBusy("save");
        setPreviewPages([]);
        setIsPdfLoading(true);
        setSelectedDocId(id);
        setSelectedInvoiceId(null);
        setSubView("viewDocument");
        try {
            const preview = await request<{ pages: { data: string }[] }>(`/documents/${id}/preview`);
            setPreviewPages(preview.pages.map(p => p.data));
        } catch {
            console.error("Document preview load failed");
        } finally {
            setBusy("idle");
            setIsPdfLoading(false);
        }
    }, [setBusy, setSubView]);

    return { documents, setDocuments, loadAndPreviewOldDocument, loadAndPreviewDocument };
}
