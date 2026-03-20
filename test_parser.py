import sys
import os
sys.path.insert(0, os.path.abspath("apps/api/src"))

from app.core.parsers.parser1c import parse_1c_statement

file_path = "/home/observer/Projects/new/doc-mini-app/KZ9496511F0008314291_2025_01_01_2025_10_19_utf_8_20251019_235052.txt"

with open(file_path, "r", encoding="utf-8") as f:
    payload = parse_1c_statement(f.read())

print(f"Bank: {payload.bank_name}")
print(f"Account: {payload.account_number}")
print(f"Transactions: {len(payload.transactions)}")

incomes = [t for t in payload.transactions if t.is_income]
expenses = [t for t in payload.transactions if not t.is_income]

print(f"Incomes: {len(incomes)}")
print(f"Expenses: {len(expenses)}")

if incomes:
    print("\nSample Income:")
    print(incomes[0])
    
if expenses:
    print("\nSample Expense:")
    print(expenses[0])
