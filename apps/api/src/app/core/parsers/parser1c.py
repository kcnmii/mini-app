import datetime
from typing import List, Optional

from app.schemas.bank import BankStatementImportPayload, BankTransactionCreate

class ParseError(Exception):
    pass

def parse_1c_statement(content: str) -> BankStatementImportPayload:
    """
    Parses a 1C-format bank statement (1CClientBankExchange)
    and returns a normalized BankStatementImportPayload.
    """
    lines = content.splitlines()
    if not lines or not lines[0].startswith("1CClientBankExchange"):
        raise ParseError("Invalid file format. Not a 1CClientBankExchange file.")

    # 1. Parse into structured blocks
    global_props = {}
    sections = []
    current_section = None
    
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("Секция"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                if current_section:
                    sections.append(current_section)
                current_section = {"_type": parts[1].strip()}
            continue
            
        if line.startswith("Конец"):
            if current_section:
                sections.append(current_section)
                current_section = None
            continue
            
        parts = line.split("=", 1)
        if len(parts) == 2:
            key, val = parts[0].strip(), parts[1].strip()
            if current_section is not None:
                current_section[key] = val
            else:
                global_props[key] = val

    # 2. Extract global account info
    # Usually "РасчСчет" holds the IBAN
    # Fallback to the account found in СекцияРасчСчет
    account_number = global_props.get("РасчСчет")
    bank_name = global_props.get("Отправитель", "")
    
    if not account_number:
        # try to find it in sections
        for sec in sections:
            if sec.get("_type") == "РасчСчет":
                if "РасчСчет" in sec:
                    account_number = sec["РасчСчет"]
                    break

    if not account_number:
        raise ParseError("Could not determine the main bank account number (РасчСчет) from the file.")

    # 3. Process transaction documents
    transactions: List[BankTransactionCreate] = []

    for sec in sections:
        # In a 1C file, actual transactions might be inside СекцияДокумент=ПлатежноеПоручение
        # or СекцияДокумент=МемориальныйОрдер or БанковскийОрдер
        # We process any document that has a date and amount
        if sec.get("_type") in ["Выписка", "РасчСчет"]: 
            continue # These are summary/meta sections

        raw_date = sec.get("ДатаДокумента") or sec.get("ДатаВалютирования") or sec.get("ДатаОперации")
        raw_sum = sec.get("Сумма")
        if not raw_date or not raw_sum:
            continue

        try:
            # Format is usually DD.MM.YYYY
            dt = datetime.datetime.strptime(raw_date, "%d.%m.%Y")
            amount = float(raw_sum)
        except ValueError:
            continue

        # Determine if it's income or expense based on recipient/payer IIC
        payer_iic = sec.get("ПлательщикИИК", "")
        receiver_iic = sec.get("ПолучательИИК", "")
        
        # Default is_income logic
        is_income = True
        
        if payer_iic == account_number:
            is_income = False  # Money left our account
        elif receiver_iic == account_number:
            is_income = True   # Money entered our account
        else:
            # If neither matches exactly, look at "СуммаПриход" or "СуммаРасход" 
            # (although these are usually on the upper "Выписка" level, not inside the doc itself)
            # Defaulting to expense if not matched as incoming
            is_income = False

        sender_name = sec.get("ПлательщикНаименование" if is_income else "ПолучательНаименование", "")
        sender_bin = sec.get("ПлательщикБИН_ИИН" if is_income else "ПолучательБИН_ИИН", "")
        
        description = sec.get("НазначениеПлатежа", "")
        doc_num = sec.get("НомерДокумента", "")

        tx = BankTransactionCreate(
            date=dt,
            amount=amount,
            sender_name=sender_name,
            sender_bin=sender_bin,
            description=description,
            is_income=is_income,
            doc_num=doc_num
        )
        transactions.append(tx)

    return BankStatementImportPayload(
        account_number=account_number,
        bank_name=bank_name,
        transactions=transactions
    )
