export interface BankInfo {
    bik: string;
    name: string;
}

export const KAZAKHSTAN_BANKS: Record<string, BankInfo> = {
    '949': { bik: 'ATYNKZKA', name: 'АО "Altyn Bank" (ДБ China Citic Bank Corporation Limited)' },
    '913': { bik: 'BKCHKZKA', name: 'АО ДБ "БАНК КИТАЯ В КАЗАХСТАНЕ"' },
    '914': { bik: 'BRKEKZKA', name: 'АО "Bereke Bank" (дочерний банк Lesha Bank LLC (Public))' },
    '722': { bik: 'CASPKZKA', name: 'АО "KASPI BANK"' },
    '766': { bik: 'CEDUKZKA', name: 'АО "Центральный Депозитарий Ценных Бумаг"' },
    '832': { bik: 'CITIKZKA', name: 'АО "Ситибанк Казахстан"' },
    '907': { bik: 'DVKAKZKA', name: 'АО "Банк Развития Казахстана"' },
    '700': { bik: 'EABRKZKA', name: 'ЕВРАЗИЙСКИЙ БАНК РАЗВИТИЯ' },
    '948': { bik: 'EURIKZKA', name: 'АО "Евразийский Банк"' },
    '009': { bik: 'GCVPKZ2A', name: 'НАО Государственная корпорация "Правительство для граждан"' },
    '972': { bik: 'HCSKKZKA', name: 'АО "Жилищный строительный сберегательный банк "Отбасы банк"' },
    '246': { bik: 'HLALKZKZ', name: 'АО «Исламский Банк «ADCB»' },
    '601': { bik: 'HSBKKZKX', name: 'АО "Народный Банк Казахстана"' },
    '930': { bik: 'ICBKKZKX', name: 'АО "Торгово-промышленный Банк Китая в г. Алматы"' },
    '550': { bik: 'INEARUMM', name: 'г.Москва Межгосударственный Банк' },
    '886': { bik: 'INLMKZKA', name: 'АО "Home Credit Bank" (ДБ АО "ForteBank")' },
    '965': { bik: 'IRTYKZKA', name: 'АО "ForteBank"' },
    '715': { bik: 'KCCJKZKK', name: 'АО "Клиринговый центр KASE"' },
    '856': { bik: 'KCJBKZKX', name: 'АО "Банк ЦентрКредит"' },
    '927': { bik: 'KICEKZKX', name: 'АО "Казахстанская фондовая биржа"' },
    '821': { bik: 'KINCKZKA', name: 'АО "Bank "Bank RBK"' },
    '070': { bik: 'KKMFKZ2A', name: 'РГУ "Комитет государственного казначейства МФ РК"' },
    '719': { bik: 'KMFBKZKK', name: 'Aкционерное общество "KMF Банк"' },
    '563': { bik: 'KPSTKZKA', name: 'АО "КАЗПОЧТА"' },
    '551': { bik: 'KSNVKZKA', name: 'АО "Фридом Банк Казахстан"' },
    '885': { bik: 'KZIBKZKA', name: 'АО "ДБ "КАЗАХСТАН-ЗИРААТ ИНТЕРНЕШНЛ БАНК"' },
    '724': { bik: 'MOKFKZKA', name: 'Акционерное общество «Коммерческий Банк БиЭнКей»' },
    '125': { bik: 'NBRKKZKX', name: 'РГУ Национальный Банк Республики Казахстан' },
    '849': { bik: 'NURSKZKX', name: 'АО "Нурбанк"' },
    '435': { bik: 'SHBKKZKA', name: 'АО "Шинхан Банк Казахстан"' },
    '998': { bik: 'TSESKZKA', name: 'АО "Alatau City Bank"' },
    '432': { bik: 'VTBAKZKZ', name: 'ДО АО Банк ВТБ (Казахстан)' },
    '896': { bik: 'ZAJSKZ22', name: 'АО "Исламский банк "Заман-Банк"' },
};

export function getBankByIIK(iik: string): BankInfo | null {
    if (!iik) return null;
    const cleanIIK = iik.replace(/\s/g, '').toUpperCase();
    if (!cleanIIK.startsWith('KZ') || cleanIIK.length < 7) return null;
    const bankCode = cleanIIK.substring(4, 7);
    return KAZAKHSTAN_BANKS[bankCode] || null;
}
