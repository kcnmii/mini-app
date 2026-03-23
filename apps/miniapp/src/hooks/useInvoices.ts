import { useState, useCallback } from "react";
import { request, makeInitialInvoice, buildInvoicePatch, parseMoney, formatMoney, API_BASE_URL } from "../utils";
import type { InvoiceForm, InvoiceRecord, DashboardSummary, DocumentRecord, Client, CatalogItem, DocumentItem, SupplierProfileData } from "../types";

export function useInvoices(setStatus: (s: string) => void, setBusy: (b: any) => void, profile: SupplierProfileData, setSubView: (v: any) => void) {
    const [invoice, setInvoice] = useState<InvoiceForm>(makeInitialInvoice(profile));
    const [invoiceRecords, setInvoiceRecords] = useState<InvoiceRecord[]>([]);
    const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary>({ awaiting: 0, overdue: 0, paid_this_month: 0, invoices_count: 0, overdue_count: 0 });
    const [selectedInvoiceId, setSelectedInvoiceId] = useState<number | null>(null);
    const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
    const [previewPages, setPreviewPages] = useState<string[]>([]);
    const [isPdfLoading, setIsPdfLoading] = useState(false);
    const [invoiceClientSearch, setInvoiceClientSearch] = useState("");

    const updateItem = useCallback((index: number, key: keyof DocumentItem, value: string) => {
        setInvoice((c) => {
            const ni = c.items.map((it, ii) => ii === index ? { ...it, [key]: value } : it);
            return { ...c, ...buildInvoicePatch(ni) };
        });
    }, []);

    const addRow = useCallback((item?: CatalogItem) => {
        setInvoice((c) => {
            const ni = [...c.items, {
                number: c.items.length + 1,
                name: item?.name ?? "",
                quantity: "1",
                unit: item?.unit ?? "шт.",
                price: item ? String(item.price) : "",
                total: item ? formatMoney(item.price) : "0",
                code: item?.sku ?? ""
            }];
            return { ...c, ...buildInvoicePatch(ni) };
        });
    }, []);

    const removeRow = useCallback((index: number) => {
        setInvoice((c) => {
            const ni = c.items.filter((_, ii) => ii !== index);
            return { ...c, ...buildInvoicePatch(ni) };
        });
    }, []);

    const changeQuantity = useCallback((index: number, delta: number) => {
        setInvoice((c) => {
            const ni = c.items.map((it, ii) => {
                if (ii !== index) return it;
                const nq = Math.max(1, (parseFloat(it.quantity) || 0) + delta);
                return { ...it, quantity: String(nq) };
            });
            return { ...c, ...buildInvoicePatch(ni) };
        });
    }, []);

    const selectClient = useCallback((client: Client) => {
        setInvoice((c) => ({ ...c, CLIENT_NAME: client.name, CLIENT_IIN: client.bin_iin, CLIENT_ADDRESS: client.address || "", CLIENT_ID: client.id }));
        setInvoiceClientSearch(client.name);
        setStatus(`Клиент: ${client.name}`);
    }, [setStatus]);

    const openNewInvoice = useCallback(async () => {
        const fresh = makeInitialInvoice(profile);
        setInvoice(fresh);
        setInvoiceClientSearch("");
        setSubView("invoiceForm");
        setSelectedDocId(null);
        setSelectedInvoiceId(null);
        try {
            const { next_number } = await request<{ next_number: string }>("/documents/next-number");
            setInvoice(c => ({ ...c, INVOICE_NUMBER: next_number }));
        } catch (e) {
            console.error("Failed to fetch next number", e);
        }
    }, [profile, setSubView]);

    const loadAndPreviewNewInvoice = useCallback(async (id: number) => {
        setBusy("save");
        setPreviewPages([]);
        setIsPdfLoading(true);
        try {
            const inv = await request<InvoiceRecord>(`/invoices/${id}`);
            setSelectedDocId(null);
            setSelectedInvoiceId(id);

            const reconstructed = makeInitialInvoice(profile);
            reconstructed.INVOICE_NUMBER = inv.number;
            if (inv.date) {
                const dparts = inv.date.split('T')[0].split('-');
                reconstructed.INVOICE_DATE = `${dparts[2]}.${dparts[1]}.${dparts[0]}`;
            }
            if (inv.due_date) {
                const uparts = inv.due_date.split('T')[0].split('-');
                reconstructed.DUE_DATE = `${uparts[2]}.${uparts[1]}.${uparts[0]}`;
            }
            reconstructed.CLIENT_NAME = inv.client_name;
            reconstructed.CLIENT_IIN = inv.client_bin;
            reconstructed.DEAL_REFERENCE = inv.deal_reference;
            reconstructed.CONTRACT = inv.deal_reference || "Договор без номера";
            reconstructed.PAYMENT_CODE = inv.payment_code;
            reconstructed.items = inv.line_items.map((it, idx) => ({
                number: idx + 1,
                name: it.name,
                quantity: String(it.quantity),
                unit: it.unit,
                price: formatMoney(it.price),
                total: formatMoney(it.total),
                code: it.code || ""
            }));

            // Sync with calculated totals (Items line, Sum in words, etc.)
            Object.assign(reconstructed, buildInvoicePatch(reconstructed.items));

            setInvoice(reconstructed);
            setInvoiceClientSearch(inv.client_name);
            setSubView("viewDocument");

            try {
                const preview = await request<{ pages: { data: string }[] }>(`/invoices/${id}/preview`);
                setPreviewPages(preview.pages.map(p => p.data));
            } catch {
                console.error("preview load failed");
            }
        } catch (e) {
            setStatus("Ошибка загрузки");
        } finally {
            setBusy("idle");
            setIsPdfLoading(false);
        }
    }, [profile, setBusy, setStatus, setSubView]);

    const saveInvoice = useCallback(async (loadData: () => void, setDocuments: (fn: any) => void) => {
        setBusy("save");
        setStatus("Сохранение...");
        try {
            const payloadDate = invoice.INVOICE_DATE.split('.').reverse().join('-');
            const docRequest = request<DocumentRecord>("/documents/invoice", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payload: invoice }) });

            const newInvBody = {
                number: invoice.INVOICE_NUMBER,
                date: payloadDate,
                due_date: invoice.DUE_DATE || null,
                client_id: (invoice as any).CLIENT_ID || null,
                client_name: invoice.CLIENT_NAME,
                client_bin: invoice.CLIENT_IIN,
                deal_reference: invoice.DEAL_REFERENCE || "",
                payment_code: invoice.PAYMENT_CODE || "",
                items: invoice.items.map(i => ({
                    name: i.name || "Позиция",
                    quantity: parseFloat(i.quantity) || 1,
                    unit: i.unit,
                    price: parseMoney(i.price),
                    total: parseMoney(i.total),
                    code: i.code
                }))
            };

            let newDoc: DocumentRecord | null = null;
            try {
                newDoc = await docRequest;
                setDocuments((c: DocumentRecord[]) => [newDoc!, ...c].slice(0, 50));
            } catch (e) { console.error("document API error", e); }

            if (!selectedDocId) {
                try {
                    await request<InvoiceRecord>("/invoices", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newInvBody) });
                } catch (e) { console.error("invoice API error", e); }
            }

            setStatus("Счет сохранен");
            setSubView(null);
            setSelectedDocId(null);
            setSelectedInvoiceId(null);
            loadData();
        } catch (e) {
            setStatus(e instanceof Error ? e.message : "Ошибка");
        } finally {
            setBusy("idle");
        }
    }, [invoice, selectedDocId, setBusy, setStatus, setSubView]);

    const deleteInvoice = useCallback(async (setDocuments: (fn: any) => void) => {
        if (!selectedDocId && !selectedInvoiceId) return;
        if (!confirm("Вы уверены, что хотите удалить этот счет?")) return;

        if (selectedInvoiceId) {
            const deletedId = selectedInvoiceId;
            const backup = invoiceRecords;
            setInvoiceRecords((c) => c.filter(d => d.id !== deletedId));
            setStatus("Счет удален");
            setSubView(null);
            setSelectedDocId(null);
            setSelectedInvoiceId(null);
            request(`/invoices/${deletedId}`, { method: "DELETE" })
                .catch(() => { setInvoiceRecords(backup); setStatus("Ошибка: не удалось удалить счет"); });
        } else if (selectedDocId) {
            const deletedId = selectedDocId;
            request(`/documents/${deletedId}`, { method: "DELETE" })
                .then(() => {
                    setDocuments((c: DocumentRecord[]) => c.filter(d => d.id !== deletedId));
                    setStatus("Документ удален");
                    setSubView(null);
                    setSelectedDocId(null);
                    setSelectedInvoiceId(null);
                })
                .catch(() => { setStatus("Ошибка: не удалось удалить документ"); });
        }
    }, [selectedDocId, selectedInvoiceId, invoiceRecords, setStatus, setSubView]);

    const markInvoicePaid = useCallback(async (invoiceId: number, refresh: () => void) => {
        try {
            await request(`/invoices/${invoiceId}/pay`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
            setStatus("Счёт отмечен как оплаченный ✅");
            refresh();
        } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка"); }
    }, [setStatus]);

    const markInvoiceSent = useCallback(async (invoiceId: number, refresh: () => void) => {
        try {
            await request(`/invoices/${invoiceId}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "sent" }) });
            setStatus("Счёт отмечен как отправленный");
            refresh();
        } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка"); }
    }, [setStatus]);

    const generatePdf = useCallback(async () => {
        setBusy("pdf");
        try {
            const r = await fetch(`${API_BASE_URL}/render/invoice/pdf`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(invoice) });
            if (!r.ok) throw new Error(await r.text());
            const b = await r.blob(); window.open(URL.createObjectURL(b), "_blank"); setStatus("PDF сгенерирован");
        } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка PDF"); } finally { setBusy("idle"); }
    }, [invoice, setBusy, setStatus]);

    const sendInvoice = useCallback(async (chatId: string) => {
        setBusy("send");
        try {
            // Build a rich caption with invoice details
            const parts: string[] = [];
            parts.push(`📄 Счет ${invoice.INVOICE_NUMBER}`);
            if (invoice.CLIENT_NAME) parts.push(`👤 ${invoice.CLIENT_NAME}`);
            if (invoice.INVOICE_DATE) parts.push(`📅 от ${invoice.INVOICE_DATE}`);
            if (invoice.TOTAL_SUM && invoice.TOTAL_SUM !== "0") parts.push(`💰 ${invoice.TOTAL_SUM} ₸`);
            const caption = parts.join("\n");

            await request("/telegram/send-invoice", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: Number(chatId), payload: invoice, caption }) });
            setStatus("Отправлено в Telegram");
        } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка отправки"); } finally { setBusy("idle"); }
    }, [invoice, setBusy, setStatus]);

    const sendReminder = useCallback(async (invoiceId: number) => {
        setBusy("remind");
        try {
            await request(`/invoices/${invoiceId}/remind`, { method: "POST" });
            setStatus("Напоминание отправлено в Telegram 🔔");
        } catch (e) {
            setStatus(e instanceof Error ? e.message : "Ошибка отправки");
        } finally {
            setBusy("idle");
        }
    }, [setBusy, setStatus]);

    const generateDocument = useCallback(async (invoiceId: number, docType: "act" | "waybill") => {
        setBusy("generate");
        try {
            const result = await request<{ status: string; title: string }>(`/invoices/${invoiceId}/generate-document?doc_type=${docType}`, { method: "POST" });
            setStatus(`${docType === "act" ? "Акт" : "Накладная"} создан(а) и отправлен(а) в Telegram ✅`);
            return result;
        } catch (e) {
            setStatus(e instanceof Error ? e.message : "Ошибка генерации");
            return null;
        } finally {
            setBusy("idle");
        }
    }, [setBusy, setStatus]);

    return {
        invoice, setInvoice, invoiceRecords, setInvoiceRecords, dashboardSummary, setDashboardSummary,
        selectedInvoiceId, setSelectedInvoiceId, selectedDocId, setSelectedDocId,
        previewPages, setPreviewPages, isPdfLoading, setIsPdfLoading,
        invoiceClientSearch, setInvoiceClientSearch,
        updateItem, addRow, removeRow, changeQuantity, selectClient, openNewInvoice,
        loadAndPreviewNewInvoice, saveInvoice, deleteInvoice, markInvoicePaid, markInvoiceSent, generatePdf, sendInvoice, sendReminder, generateDocument
    };
}
