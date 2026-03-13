import type { SupplierProfileData, InvoiceForm, DocumentItem } from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
export const DEFAULT_TEST_CHAT_ID = import.meta.env.VITE_TELEGRAM_TEST_CHAT_ID ?? "8134372922";

export const emptyProfile: SupplierProfileData = {
    company_name: "", company_iin: "", company_iic: "", company_bic: "", company_kbe: "",
    beneficiary_bank: "", payment_code: "", supplier_name: "", supplier_iin: "",
    supplier_address: "", executor_name: "", position: "", phone: "", email: "",
    logo_path: "", signature_path: "", stamp_path: "",
};

export const AVATAR_COLORS = [
    "#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#007AFF", "#5856D6", "#AF52DE",
];

export function getAvatarColor(name: string) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export function makeInitialInvoice(profile?: SupplierProfileData): InvoiceForm {
    const p = profile ?? emptyProfile;
    return {
        INVOICE_NUMBER: "СФ-001", INVOICE_DATE: new Date().toLocaleDateString("ru-RU"),
        CONTRACT: "Договор без номера",
        SUPPLIER_NAME: p.supplier_name || "ТОО Demo Supplier",
        SUPPLIER_IIN: p.supplier_iin || "123456789012",
        SUPPLIER_ADDRESS: p.supplier_address || "г. Алматы, ул. Абая, 10",
        COMPANY_NAME: p.company_name || "ТОО Demo Supplier",
        COMPANY_IIN: p.company_iin || "123456789012",
        COMPANY_IIC: p.company_iic || "KZ123456789012345678",
        COMPANY_BIC: p.company_bic || "KCJBKZKX",
        COMPANY_KBE: p.company_kbe || "17",
        BENEFICIARY_BANK: p.beneficiary_bank || "АО Банк Demo",
        PAYMENT_CODE: p.payment_code || "710",
        CLIENT_NAME: "", CLIENT_IIN: "", CLIENT_ADDRESS: "",
        EXECUTOR_NAME: p.executor_name || "Иван Иванов",
        POSITION: p.position || "Директор",
        VAT: "Без НДС", ITEMS_TOTAL_LINE: "1", TOTAL_SUM: "0",
        TOTAL_SUM_IN_WORDS: "Ноль тенге 00 тиын",
        items: [],
        INCLUDE_LOGO: !!p.logo_path, INCLUDE_SIGNATURE: !!p.signature_path, INCLUDE_STAMP: !!p.stamp_path,
    };
}

export function getTelegramWebApp() { return window.Telegram?.WebApp; }

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, options);
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<T>;
}

export function parseMoney(value: string): number {
    const n = value.replace(/\s+/g, "").replace(",", ".");
    const p = Number(n);
    return Number.isFinite(p) ? p : 0;
}

export function formatMoney(value: number): string {
    return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value);
}

function pluralize(value: number, forms: [string, string, string]): string {
    const m10 = value % 10, m100 = value % 100;
    if (m100 >= 11 && m100 <= 19) return forms[2];
    if (m10 === 1) return forms[0];
    if (m10 >= 2 && m10 <= 4) return forms[1];
    return forms[2];
}

function numberToWordsRu(value: number): string {
    const unitsMale = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"];
    const unitsFemale = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"];
    const teens = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"];
    const tens = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"];
    const hundreds = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"];
    const groups = [
        { forms: ["", "", ""] as [string, string, string], female: false },
        { forms: ["тысяча", "тысячи", "тысяч"] as [string, string, string], female: true },
        { forms: ["миллион", "миллиона", "миллионов"] as [string, string, string], female: false },
    ];
    if (value === 0) return "ноль";
    const parts: string[] = [];
    let remainder = Math.floor(value), groupIndex = 0;
    while (remainder > 0) {
        const chunk = remainder % 1000;
        if (chunk > 0) {
            const cp: string[] = [];
            const h = Math.floor(chunk / 100), t = Math.floor((chunk % 100) / 10), u = chunk % 10;
            const units = groups[groupIndex]?.female ? unitsFemale : unitsMale;
            if (h > 0) cp.push(hundreds[h]);
            if (t === 1) { cp.push(teens[u]); } else {
                if (t > 1) cp.push(tens[t]);
                if (u > 0) cp.push(units[u]);
            }
            if (groupIndex > 0) cp.push(pluralize(chunk, groups[groupIndex].forms));
            parts.unshift(...cp.filter(Boolean));
        }
        remainder = Math.floor(remainder / 1000);
        groupIndex += 1;
    }
    return parts.join(" ");
}

export function moneyToWords(value: number): string {
    const ip = Math.floor(value), fp = Math.round((value - ip) * 100);
    const w = numberToWordsRu(ip);
    return `${w.charAt(0).toUpperCase() + w.slice(1)} ${pluralize(ip, ["тенге", "тенге", "тенге"])} ${String(fp).padStart(2, "0")} тиын`;
}

export function buildInvoicePatch(items: DocumentItem[]) {
    const ni = items.map((item, i) => {
        const total = parseMoney(item.quantity) * parseMoney(item.price);
        return { ...item, number: i + 1, total: formatMoney(total) };
    });
    const gt = ni.reduce((s, it) => s + parseMoney(it.total), 0);
    return { items: ni, ITEMS_TOTAL_LINE: String(ni.length), TOTAL_SUM: formatMoney(gt), TOTAL_SUM_IN_WORDS: moneyToWords(gt) };
}
