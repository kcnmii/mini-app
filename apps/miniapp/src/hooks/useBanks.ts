import { useState, useCallback } from "react";
import { request } from "../utils";
// import { parse1CFile } from "../utils/oneCParser"; // Backend parses it now

export function useBanks(setStatus: (s: string) => void, setBusy: (b: any) => void, setSubView: (v: any) => void) {
    const [bankAccounts, setBankAccounts] = useState<{ id: number; bank_name: string; account_number: string; bic: string; currency: string; is_default: boolean }[]>([]);
    const [selectedBankAccountId, setSelectedBankAccountId] = useState<number | null>(null);
    const [importResult, setImportResult] = useState<any | null>(null);

    const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>, profileIic: string, refreshAll: () => void) => {
        const file = e.target.files?.[0];
        if (!file) return;

        try {
            setBusy("save");
            setImportResult(null);
            setSubView("importSuccess");

            const formData = new FormData();
            formData.append("file", file);

            const res = await request<any>("/banks/upload-1c", {
                method: "POST",
                body: formData
            });

            setImportResult(res);

            if (res.auto_matched_count > 0) {
                refreshAll();
            }
        } catch (error) {
            console.error("1C Parse Error", error);
            setStatus("Ошибка при чтении файла 1С: " + String(error));
        } finally {
            setBusy("idle");
            if (e.target) e.target.value = '';
        }
    }, [setBusy, setStatus, setSubView]);

    return { bankAccounts, setBankAccounts, selectedBankAccountId, setSelectedBankAccountId, handleFileUpload, importResult, setImportResult };
}
