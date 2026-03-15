import { getBankByIIK } from "./bankAutofill";

export const parse1CFile = (text: string, myAccountNumber: string) => {
    const lines = text.split('\n');
    let currentSection = '';
    let accountInfo: any = {};
    let documents: any[] = [];
    let currentDoc: any = {};

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        const upperLine = trimmed.toUpperCase();
        if (upperLine.startsWith('СЕКЦИЯРАСЧСЧЕТ')) {
            currentSection = 'account';
            continue;
        } else if (upperLine.startsWith('КОНЕЦРАСЧСЧЕТ')) {
            currentSection = '';
            continue;
        } else if (upperLine.startsWith('СЕКЦИЯДОКУМЕНТ')) {
            currentSection = 'document';
            continue;
        } else if (upperLine.startsWith('КОНЕЦДОКУМЕНТА')) {
            documents.push(currentDoc);
            currentDoc = {};
            currentSection = '';
            continue;
        }

        const parts = trimmed.split('=');
        if (parts.length < 2) continue;
        const key = parts[0].trim().toUpperCase();
        const value = parts.slice(1).join('=').trim();

        if (currentSection === 'account' && key === 'РАСЧСЧЕТ') accountInfo.number = value.trim();
        else if (currentSection === 'document') currentDoc[key] = value;
        else if (!currentSection && key === 'РАСЧСЧЕТ' && !accountInfo.number) accountInfo.number = value.trim();
    }

    if (!accountInfo.number && !myAccountNumber) {
        throw new Error("Account number not found in file and not provided");
    }

    const targetAccountNumber = accountInfo.number || myAccountNumber;
    const bankInfo = getBankByIIK(targetAccountNumber);
    const bankName = bankInfo ? bankInfo.name : `Счет ${targetAccountNumber.slice(-4)}`;

    const parseAmount = (val: string) => val ? parseFloat(val.replace(',', '.').replace(/\s/g, '')) : 0;
    const myAccNormalized = targetAccountNumber.trim().replace(/^0+/, '');
    const transactions = [];

    for (const doc of documents) {
        let amount = 0;
        let is_income = true;

        const sumIn = doc['СУММАПРИХОД'];
        const sumOut = doc['СУММАРАСХОД'];
        const sumGeneral = doc['СУММА'];

        if (sumIn && parseAmount(sumIn) > 0) {
            amount = parseAmount(sumIn);
            is_income = true;
        } else if (sumOut && parseAmount(sumOut) > 0) {
            amount = parseAmount(sumOut);
            is_income = false;
        } else if (sumGeneral && parseAmount(sumGeneral) > 0) {
            const payerIIK = (doc['ПЛАТЕЛЬЩИКИИК'] || '').trim().replace(/^0+/, '');
            const receiverIIK = (doc['ПОЛУЧАТЕЛЬИИК'] || '').trim().replace(/^0+/, '');
            amount = parseAmount(sumGeneral);
            if (payerIIK === myAccNormalized) is_income = false;
            else if (receiverIIK === myAccNormalized) is_income = true;
        }

        if (amount === 0) continue;

        const dateStr = doc['ДАТАДОКУМЕНТА'] || doc['ДАТАОПЕРАЦИИ'] || "";
        let dateIso = new Date().toISOString();
        if (dateStr) {
            const dateParts = dateStr.split('.');
            if (dateParts.length === 3) dateIso = `${dateParts[2]}-${dateParts[1]}-${dateParts[0]}T00:00:00Z`;
        }

        const payerName = doc['ПЛАТЕЛЬЩИКНАИМЕНОВАНИЕ'] || 'Неизвестный плательщик';
        const receiverName = doc['ПОЛУЧАТЕЛЬНАИМЕНОВАНИЕ'] || 'Неизвестный получатель';
        const purpose = doc['НАЗНАЧЕНИЕПЛАТЕЖА'] || '';

        const payerBin = doc['ПЛАТЕЛЬЩИКБИН_ИИН'] || doc['ПЛАТЕЛЬЩИКБИН'] || doc['ПЛАТЕЛЬЩИКРНН'] || '';
        const receiverBin = doc['ПОЛУЧАТЕЛЬБИН_ИИН'] || doc['ПОЛУЧАТЕЛЬБИН'] || doc['ПОЛУЧАТЕЛЬРНН'] || '';

        let sender_name = is_income ? payerName : receiverName;
        let sender_bin = (is_income ? payerBin : receiverBin).replace(/\D/g, '');

        transactions.push({
            date: dateIso,
            amount: amount,
            sender_name,
            sender_bin,
            description: purpose,
            is_income,
            doc_num: doc['НОМЕРДОКУМЕНТА'] || ""
        });
    }

    return {
        account_number: targetAccountNumber,
        bank_name: bankName,
        transactions
    };
};
