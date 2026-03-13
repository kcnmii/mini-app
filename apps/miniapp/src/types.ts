export type TabKey = "home" | "invoices" | "clients" | "items" | "profile";

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

export type Client = {
    id: number; name: string; bin_iin: string; contact_name: string; phone: string; created_at: string;
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
};

export type DocumentRecord = {
    id: number; title: string; client_name: string; total_sum: string;
    total_sum_in_words: string; pdf_path: string; created_at: string;
};

export type ClientDraft = { name: string; bin_iin: string; contact_name: string; phone: string };
export type ItemDraft = { name: string; unit: string; price: string; sku: string };

export type SupplierProfileData = {
    company_name: string; company_iin: string; company_iic: string;
    company_bic: string; company_kbe: string; beneficiary_bank: string;
    payment_code: string; supplier_name: string; supplier_iin: string;
    supplier_address: string; executor_name: string; position: string;
    phone: string; email: string; logo_path: string; signature_path: string; stamp_path: string;
};
