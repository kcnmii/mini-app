import { useState, useEffect, useRef, useCallback } from "react";

type SubViewType = null | "invoiceForm" | "addClient" | "addItem" | "editRequisites" | "addBankAccount" | "viewDocument" | "addClientBankAccount" | "addClientContact" | "dateFilter" | "bankPicker" | "importSuccess";

export function useSharedState() {
    const [status, setStatus] = useState("");
    const [busy, setBusy] = useState<"idle" | "save" | "send" | "pdf">("idle");
    const [subView, setSubViewRaw] = useState<SubViewType>(null);
    const [prevSubView, setPrevSubView] = useState<SubViewType>(null);
    const [isBinLoading, setIsBinLoading] = useState(false);
    const rootScrollY = useRef<number>(0);

    const setSubView = useCallback((newView: SubViewType) => {
        setPrevSubView(subView); // Track previous subView
        if (newView !== null) {
            // We're opening a subview
            if (subView === null) {
                // If we're coming from the root tabs, save the scroll position
                rootScrollY.current = window.scrollY;
            }
            // Immediately scroll to top so the new view animation starts from the top
            window.scrollTo(0, 0);
        } else {
            // We're closing back to the root tabs
            if (subView !== null) {
                // Wait for React to render the root DOM nodes before attempting to scroll down
                setTimeout(() => window.scrollTo(0, rootScrollY.current), 10);
            }
        }
        setSubViewRaw(newView);
    }, [subView]);

    // Status banner auto-hide
    useEffect(() => {
        if (!status) return;
        const t = setTimeout(() => setStatus(""), 3000);
        return () => clearTimeout(t);
    }, [status]);

    return { status, setStatus, busy, setBusy, subView, setSubView, prevSubView, isBinLoading, setIsBinLoading };
}
