import { useState, useCallback } from "react";
import { request, emptyProfile, makeInitialInvoice } from "../utils";
import type { SupplierProfileData, InvoiceForm } from "../types";

export function useProfile(setStatus: (s: string) => void, setBusy: (b: any) => void, setInvoice: (i: any) => void, setSubView: (v: any) => void) {
    const [profile, setProfile] = useState<SupplierProfileData>(emptyProfile);
    const [profileDraft, setProfileDraft] = useState<SupplierProfileData>(emptyProfile);

    const refreshProfileImages = useCallback(async () => {
        try {
            const p = await request<SupplierProfileData>("/profile");
            setProfile(p);
            setProfileDraft(p);
            setInvoice((c: InvoiceForm) => ({
                ...c,
                INCLUDE_LOGO: c.INCLUDE_LOGO || !!p.logo_path,
                INCLUDE_SIGNATURE: c.INCLUDE_SIGNATURE || !!p.signature_path,
                INCLUDE_STAMP: c.INCLUDE_STAMP || !!p.stamp_path,
            }));
        } catch { }
    }, [setInvoice]);

    const saveProfile = useCallback(async () => {
        setBusy("save");
        try {
            const s = await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profileDraft) });
            setProfile(s);
            setProfileDraft(s);
            setInvoice(makeInitialInvoice(s));
            setStatus("Профиль сохранён");
        } catch (e) {
            setStatus(e instanceof Error ? e.message : "Ошибка");
        } finally {
            setBusy("idle");
        }
    }, [profileDraft, setBusy, setStatus, setInvoice]);

    const deleteRequisites = useCallback(async () => {
        if (!confirm("Вы уверены, что хотите удалить реквизиты?")) return;
        const cleared = { ...profile, company_iin: "", company_name: "", supplier_address: "", executor_name: "", position: "", phone: "", email: "" };
        setBusy("save");
        try {
            const s = await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cleared) });
            setProfile(s);
            setProfileDraft(s);
            setInvoice(makeInitialInvoice(s));
            setStatus("Реквизиты удалены");
            setSubView(null);
        } catch (e) {
            setStatus(e instanceof Error ? e.message : "Ошибка");
        } finally {
            setBusy("idle");
        }
    }, [profile, setBusy, setStatus, setInvoice, setSubView]);

    const deleteBankAccount = useCallback(async () => {
        if (!confirm("Вы уверены, что хотите удалить банковский счет?")) return;
        const cleared = { ...profile, company_iic: "", company_bic: "", beneficiary_bank: "" };
        setBusy("save");
        try {
            const s = await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cleared) });
            setProfile(s);
            setProfileDraft(s);
            setInvoice(makeInitialInvoice(s));
            setStatus("Счет удален");
            setSubView(null);
        } catch (e) {
            setStatus(e instanceof Error ? e.message : "Ошибка");
        } finally {
            setBusy("idle");
        }
    }, [profile, setBusy, setStatus, setInvoice, setSubView]);

    return { profile, setProfile, profileDraft, setProfileDraft, refreshProfileImages, saveProfile, deleteRequisites, deleteBankAccount };
}
