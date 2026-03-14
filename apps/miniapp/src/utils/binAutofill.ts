import { request } from "../utils";

export interface BinInfo {
    name: string;
    address: string;
    bin: string;
    director?: string;
    type?: 'ЮЛ' | 'ИП';
}

export async function fetchCompanyByBin(bin: string): Promise<BinInfo | null> {
    const cleanBin = bin.trim().replace(/\s/g, '').replace(/-/g, '');
    if (!cleanBin || cleanBin.length !== 12) return null;

    try {
        const data = await request<any>(`/clients/search-bin/${cleanBin}`);
        if (data && data.found) {
            return {
                name: data.name || '',
                address: data.address || '',
                bin: data.bin || cleanBin,
                director: data.director || '',
                type: data.type === 'IP' ? 'ИП' : 'ЮЛ'
            };
        }
        return null;
    } catch (error) {
        console.error('Error fetching BIN data:', error);
        return null;
    }
}
