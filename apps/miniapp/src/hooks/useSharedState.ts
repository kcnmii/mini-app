import { useState, useEffect } from "react";

export function useSharedState() {
    const [status, setStatus] = useState("");
    const [busy, setBusy] = useState<"idle" | "save" | "send" | "pdf">("idle");
    const [subView, setSubView] = useState<null | "invoiceForm" | "addClient" | "addItem" | "editRequisites" | "addBankAccount" | "viewDocument" | "addClientBankAccount" | "addClientContact" | "dateFilter" | "bankPicker" | "importSuccess">(null);
    const [isBinLoading, setIsBinLoading] = useState(false);

    // Status banner auto-hide
    useEffect(() => {
        if (!status) return;
        const t = setTimeout(() => setStatus(""), 3000);
        return () => clearTimeout(t);
    }, [status]);

    return { status, setStatus, busy, setBusy, subView, setSubView, isBinLoading, setIsBinLoading };
}
