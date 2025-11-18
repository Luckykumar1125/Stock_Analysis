import fitz
import re
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class Transaction(BaseModel):
    date: str
    time: str
    transaction_type: str   # "Paid to" or "Received from"
    name: str
    amount: float


class BankStatementParser:
    DATE_REGEX = r"(\d{2} \w{3}, \d{4})"
    TIME_REGEX = r"(\d{2}:\d{2} (?:AM|PM))"
    PAID_REGEX = r"Paid to ([A-Za-z0-9 &.-]+)"
    RECEIVED_REGEX = r"Received from ([A-Za-z0-9 &.-]+)"
    AMOUNT_REGEX = r"₹([\d,]+\.?\d*)"

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_text(self) -> str:
        """Extracts raw text from PDF using PyMuPDF."""
        doc = fitz.open(self.pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        return full_text

    def parse_amount(self, amt: str) -> float:
        return float(amt.replace(",", ""))

    def parse(self) -> List[Transaction]:
        text = self.extract_text()

        transactions = []

        date_blocks = re.split(self.DATE_REGEX, text)

        if len(date_blocks) < 3:
            return []

        for i in range(1, len(date_blocks), 2):
            date_str = date_blocks[i]
            block = date_blocks[i + 1]

            # TIME
            time_match = re.search(self.TIME_REGEX, block)
            time_str = time_match.group(1) if time_match else ""

            # FIRST detect "Received from"
            received_match = re.search(self.RECEIVED_REGEX, block, re.IGNORECASE)
            paid_match = re.search(self.PAID_REGEX, block, re.IGNORECASE)

            if received_match:
                transaction_type = "Received from"
                name = received_match.group(1).strip()

            elif paid_match:
                transaction_type = "Paid to"
                name = paid_match.group(1).strip()

            else:
                continue  # skip if neither match

            # AMOUNT
            amount_match = re.search(self.AMOUNT_REGEX, block)
            if not amount_match:
                continue

            amount = self.parse_amount(amount_match.group(1))

            transactions.append(
                Transaction(
                    date=date_str,
                    time=time_str,
                    transaction_type=transaction_type,
                    name=name,
                    amount=amount
                )
            )

        return transactions


    def to_json(self) -> str:
        return [t.model_dump() for t in self.parse()]
