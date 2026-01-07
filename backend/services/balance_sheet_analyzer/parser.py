import fitz  # PyMuPDF
import re
from typing import List, Optional
from pydantic import BaseModel

class Transaction(BaseModel):
    date: str
    time: str = ""
    transaction_type: str   # "Debit" or "Credit"
    name: str
    amount: float

class BankStatementParser:
    # --- GPay / Text Regexes ---
    GPAY_DATE_REGEX = r"(\d{2} \w{3}, \d{4})"
    GPAY_TIME_REGEX = r"(\d{2}:\d{2} (?:AM|PM))"
    GPAY_PAID_REGEX = r"Paid to ([A-Za-z0-9 &.-]+)"
    GPAY_RECEIVED_REGEX = r"Received from ([A-Za-z0-9 &.-]+)"
    GPAY_AMOUNT_REGEX = r"₹([\d,]+\.?\d*)"

    # --- Generic Bank Date Regexes ---
    # Matches: 12/01/2023, 12-01-2023, 12 Jan 2023
    BANK_DATE_REGEX = r"(\d{2}[/-]\d{2}[/-]\d{4}|\d{2} \w{3} \d{4})"

    def __init__(self, pdf_input):
        # Handle both file path (str) and memory stream (bytes)
        if isinstance(pdf_input, (bytes, bytearray)):
            self.doc = fitz.open(stream=pdf_input, filetype="pdf")
        else:
            self.doc = fitz.open(pdf_input)

    def parse_amount(self, amt_str: str) -> float:
        """Cleans currency symbols and commas."""
        if not amt_str: return 0.0
        clean = amt_str.replace(",", "").replace("₹", "").replace("Rs.", "").strip()
        # Handle cases like "1,200.00 Cr"
        clean = clean.split(" ")[0] 
        try:
            return float(clean)
        except ValueError:
            return 0.0

    def parse(self) -> List[Transaction]:
        """
        Master function:
        1. Tries to find TABLES (Standard Bank Statements)
        2. If no tables, falls back to TEXT REGEX (GPay/PhonePe)
        """
        transactions = []
        
        # --- STRATEGY 1: TABLE EXTRACTION (Banks) ---
        has_tables = False
        for page in self.doc:
            # PyMuPDF's built-in table finder
            tables = page.find_tables()
            if tables:
                has_tables = True
                for tab in tables:
                    transactions.extend(self._process_table(tab.extract()))

        if has_tables and len(transactions) > 0:
            print(f"Parsed using Table Strategy: {len(transactions)} txns found")
            return transactions

        # --- STRATEGY 2: TEXT REGEX (GPay/PhonePe) ---
        # If no tables found, extract raw text and use your original regex logic
        full_text = ""
        for page in self.doc:
            full_text += page.get_text()
        
        transactions = self._process_gpay_text(full_text)
        print(f"Parsed using GPay Strategy: {len(transactions)} txns found")
        return transactions

    def _process_table(self, rows: List[List[str]]) -> List[Transaction]:
        """
        Logic to handle rows/cols from HDFC/SBI/ICICI style PDFs.
        """
        txns = []
        if not rows or len(rows) < 2:
            return []

        # 1. Identify Columns by Header (First row usually)
        headers = [h.lower().replace("\n", " ") for h in rows[0]]
        
        try:
            # Find indices of key columns
            date_idx = next(i for i, h in enumerate(headers) if "date" in h)
            desc_idx = next(i for i, h in enumerate(headers) if "particulars" in h or "description" in h or "narration" in h or "remark" in h)
            
            # Withdrawal/Debit column
            debit_idx = -1
            for i, h in enumerate(headers):
                if "debit" in h or "withdrawal" in h:
                    debit_idx = i
                    break
            
            # Deposit/Credit column
            credit_idx = -1
            for i, h in enumerate(headers):
                if "credit" in h or "deposit" in h:
                    credit_idx = i
                    break

        except StopIteration:
            # If headers not found, skip this table
            return []

        # 2. Iterate Data Rows
        for row in rows[1:]:
            # Clean up row data
            row = [str(cell).strip() for cell in row]
            
            # Skip empty rows
            if len(row) <= max(date_idx, desc_idx): continue
            
            # Validate Date
            date_str = row[date_idx]
            if not re.match(self.BANK_DATE_REGEX, date_str):
                continue # Skip rows that are just summaries/headers

            description = row[desc_idx].replace("\n", " ")
            
            # Determine Amount (Debit or Credit?)
            amount = 0.0
            type_str = "Unknown"

            # Check Debit
            if debit_idx != -1 and debit_idx < len(row) and row[debit_idx]:
                val = self.parse_amount(row[debit_idx])
                if val > 0:
                    amount = -val # Expense
                    type_str = "Debit"

            # Check Credit (Only if not a debit)
            if amount == 0 and credit_idx != -1 and credit_idx < len(row) and row[credit_idx]:
                val = self.parse_amount(row[credit_idx])
                if val > 0:
                    amount = val # Income
                    type_str = "Credit"

            if amount != 0:
                txns.append(Transaction(
                    date=date_str,
                    time="",
                    transaction_type=type_str,
                    name=description,
                    amount=amount
                ))
        
        return txns

    def _process_gpay_text(self, text: str) -> List[Transaction]:
        """
        Your original GPay logic, preserved exactly as is.
        """
        transactions = []
        date_blocks = re.split(self.GPAY_DATE_REGEX, text)

        if len(date_blocks) < 3:
            return []

        for i in range(1, len(date_blocks), 2):
            date_str = date_blocks[i]
            block = date_blocks[i + 1]

            # TIME
            time_match = re.search(self.GPAY_TIME_REGEX, block)
            time_str = time_match.group(1) if time_match else ""

            # Detect Type & Name
            received_match = re.search(self.GPAY_RECEIVED_REGEX, block, re.IGNORECASE)
            paid_match = re.search(self.GPAY_PAID_REGEX, block, re.IGNORECASE)

            if received_match:
                transaction_type = "Received from"
                name = received_match.group(1).strip()
            elif paid_match:
                transaction_type = "Paid to"
                name = paid_match.group(1).strip()
            else:
                continue 

            # Amount
            amount_match = re.search(self.GPAY_AMOUNT_REGEX, block)
            if not amount_match:
                continue

            amount = self.parse_amount(amount_match.group(1))

            if transaction_type == "Paid to":
                amount = -amount
            
            transactions.append(Transaction(
                date=date_str, 
                time=time_str, 
                transaction_type=transaction_type, 
                name=name, 
                amount=amount
            ))

        return transactions

    def to_json(self) -> List[dict]:
        return [t.model_dump() for t in self.parse()]