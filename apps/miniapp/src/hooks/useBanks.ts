import { useState, useCallback } from "react";
import { request } from "../utils";
import { parse1CFile } from "../utils/oneCParser";

export function useBanks(setStatus: (s: string) => void, setBusy: (b: any) => void) {
    const [bankAccounts, setBankAccounts] = useState<{ id: number; bank_name: string; account_number: string; bic: string; currency: string; is_default: boolean }[]>([]);
    const [selectedBankAccountId, setSelectedBankAccountId] = useState<number | null>(null);

    const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>, profileIic: string, refreshAll: () => void) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (event) => {
            try {
                setBusy("save");
                const text = event.target?.result as string;
                const payload = parse1CFile(text, profileIic || "");

                const res = await request<any>("/banks/import", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                setStatus(`Из выписки 1С получено ${res.added_count} оп. Найдено оплат счетов: ${res.matched_count} ✅`);
                if (res.matched_count > 0 || res.added_count > 0) {
                    refreshAll();
                }
            } catch (error) {
                console.error("1C Parse Error", error);
                setStatus("Ошибка при чтении файла 1С");
            } finally {
                setBusy("idle");
            }
        };
        reader.readAsText(file, "windows-1251");
        e.target.value = '';
    }, [setBusy, setStatus]);

    return { bankAccounts, setBankAccounts, selectedBankAccountId, setSelectedBankAccountId, handleFileUpload };
}
