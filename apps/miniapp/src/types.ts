export type TabKey = "home" | "invoices" | "directory" | "profile";

export type TelegramWebApp = {
    initData?: string;
    initDataUnsafe?: {
        user?: { id?: number; first_name?: string; last_name?: string; username?: string; photo_url?: string };
    };
    ready?: () => void;
    expand?: () => void;
};

declare global {
    interface Window {
        Telegram?: { WebApp?: TelegramWebApp };
    }
}

export interface BankAccount {
    id: number;
    bank_name: string;
    account_number: string;
    bic: string;
    currency: string;
    is_default: boolean;
}


export type ClientBankAccount = {
    id?: number;
    iic: string;
    bank_name: string;
    bic: string;
    kbe: string;
    is_main: boolean;
};

export type ClientContact = {
    id?: number;
    name: string;
    phone: string;
    email: string;
};

export type Client = {
    id: number;
    name: string;
    bin_iin: string;
    address: string;
    director: string;
    accounts: ClientBankAccount[];
    contacts: ClientContact[];
    created_at: string;
};

export type CatalogItem = {
    id: number; name: string; unit: string; price: number; sku: string; created_at: string;
};

export type DocumentItem = {
    number: number; name: string; quantity: string; unit: string; price: string; total: string; code: string;
};

export type InvoiceForm = {
    INVOICE_NUMBER: string; INVOICE_DATE: string; CONTRACT: string;
    SUPPLIER_NAME: string; SUPPLIER_IIN: string; SUPPLIER_ADDRESS: string;
    COMPANY_NAME: string; COMPANY_IIN: string; COMPANY_IIC: string;
    COMPANY_BIC: string; COMPANY_KBE: string; BENEFICIARY_BANK: string;
    PAYMENT_CODE: string; CLIENT_NAME: string; CLIENT_IIN: string;
    CLIENT_ADDRESS: string; EXECUTOR_NAME: string; POSITION: string;
    VAT: string; ITEMS_TOTAL_LINE: string; TOTAL_SUM: string;
    TOTAL_SUM_IN_WORDS: string; items: DocumentItem[];
    INCLUDE_LOGO: boolean; INCLUDE_SIGNATURE: boolean; INCLUDE_STAMP: boolean;
    DUE_DATE: string;           // YYYY-MM-DD format, empty if not set
    DEAL_REFERENCE: string;     // "Договор №15" or similar
};
export type ClientBalance = {
    total_invoiced: number;
    total_paid: number;
    debt: number;
};

export type DocumentRecord = {
    id: number; title: string; client_name: string; total_sum: string;
    total_sum_in_words: string; pdf_path: string; docx_path: string; created_at: string;
    edo_status?: string; doc_type?: string; share_uuid?: string;
};

export type DocumentStats = {
    count: number;
    total_sum: number;
    client_count: number;
};

export type InvoiceRecord = {
    id: number;
    number: string;
    date: string;
    due_date: string | null;
    client_id: number | null;
    client_name: string;
    client_bin: string;
    deal_reference: string;
    payment_code: string;
    status: "draft" | "sent" | "paid" | "overdue";
    total_amount: number;
    pdf_path: string;
    docx_path: string;
    created_at: string;
    updated_at: string | null;
    line_items: { id: number; name: string; quantity: number; unit: string; price: number; total: number; code: string }[];
};

export type DashboardSummary = {
    awaiting: number;
    overdue: number;
    paid_this_month: number;
    invoices_count: number;
    overdue_count: number;
};

export type ClientDraft = {
    name: string;
    bin_iin: string;
    address: string;
    director: string;
    accounts: ClientBankAccount[];
    contacts: ClientContact[];
    kbe?: string;
};
export type ItemDraft = { name: string; unit: string; price: string; sku: string };

export type SupplierProfileData = {
    company_name: string; company_iin: string; company_iic: string;
    company_bic: string; company_kbe: string; beneficiary_bank: string;
    payment_code: string; supplier_name: string; supplier_iin: string;
    supplier_address: string; executor_name: string; position: string;
    phone: string; email: string; notifications_enabled: boolean; logo_path: string; signature_path: string; stamp_path: string;
};

// ── EDO Types ──

export type EdoStatus =
    | "draft"
    | "awaiting_sign"
    | "signed_self"
    | "sent"
    | "signed_both"
    | "rejected"
    | "esf_pending"
    | "esf_submitted"
    | "completed";

export type SignatureInfo = {
    id: number;
    signer_name: string;
    signer_iin: string;
    signer_org: string;
    signer_role: "sender" | "receiver";
    certificate_serial: string;
    certificate_valid_from: string | null;
    certificate_valid_to: string | null;
    signed_at: string | null;
    signature_type: "cms" | "xml";
};

export type SigningSessionInfo = {
    signing_session_id: number;
    egov_mobile_link: string;
    egov_business_link: string;
    qr_code_b64: string;
};

export type SigningStatusInfo = {
    status: "pending" | "signed" | "expired" | "error";
    signed_at: string | null;
    signer_name: string | null;
};

export type ShareInfo = {
    share_url: string;
    share_uuid: string;
};
