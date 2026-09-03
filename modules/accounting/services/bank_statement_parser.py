"""
Bank Statement Parser Service for Nova ERP.

Supports parsing OFX (Open Financial Exchange 1.x SGML & 2.x XML), QFX, and CSV
bank statements into standardized ParsedStatement and ParsedTransaction structures.
Extracts statement metadata, transaction dates, check numbers, payees, memos,
and deposit/withdrawal amounts.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Union, Dict, Any
import re
import csv
import io


@dataclass
class ParsedTransaction:
    """Represents a single line-item transaction parsed from a bank statement."""
    transaction_date: date
    amount: float
    fit_id: Optional[str] = None
    check_number: Optional[str] = None
    payee_name: Optional[str] = None
    memo: Optional[str] = None
    transaction_type: str = "CHECK"
    match_status: str = "Pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_date": (
                self.transaction_date.isoformat()
                if isinstance(self.transaction_date, date)
                else self.transaction_date
            ),
            "fit_id": self.fit_id,
            "check_number": self.check_number,
            "payee_name": self.payee_name,
            "memo": self.memo,
            "amount": float(self.amount),
            "transaction_type": self.transaction_type,
            "match_status": self.match_status,
        }


@dataclass
class ParsedStatement:
    """Represents statement-level metadata and a list of parsed transactions."""
    bank_name: str = "Unknown Bank"
    account_number: str = "UNKNOWN"
    statement_number: Optional[str] = None
    statement_date: date = field(default_factory=date.today)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0
    file_name: Optional[str] = None
    file_type: str = "OFX"
    total_transactions: int = 0
    transactions: List[ParsedTransaction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "statement_number": self.statement_number,
            "statement_date": (
                self.statement_date.isoformat()
                if isinstance(self.statement_date, date)
                else self.statement_date
            ),
            "start_date": (
                self.start_date.isoformat()
                if isinstance(self.start_date, date)
                else self.start_date
            ),
            "end_date": (
                self.end_date.isoformat()
                if isinstance(self.end_date, date)
                else self.end_date
            ),
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "total_deposits": self.total_deposits,
            "total_withdrawals": self.total_withdrawals,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "total_transactions": self.total_transactions,
            "transactions": [t.to_dict() for t in self.transactions],
        }


def parse_date_str(val: Any) -> date:
    """Parse various string date representations into a datetime.date object."""
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()

    if not val:
        return date.today()

    s = str(val).strip()
    if not s:
        return date.today()

    # 1. OFX format: YYYYMMDDHHMMSS or YYYYMMDD (e.g. 20260901120000[0:GMT])
    ofx_match = re.match(r'^(\d{4})(\d{2})(\d{2})', s)
    if ofx_match and (len(s) == 8 or len(s) >= 14 or '[' in s):
        try:
            return date(int(ofx_match.group(1)), int(ofx_match.group(2)), int(ofx_match.group(3)))
        except ValueError:
            pass

    # 2. ISO format YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}', s):
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass

    # 3. Slash format YYYY/MM/DD
    if re.match(r'^\d{4}/\d{2}/\d{2}', s):
        parts = s[:10].split('/')
        try:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            pass

    # 4. YYYYMMDD standalone
    if len(s) == 8 and s.isdigit():
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            pass

    # 5. Slash formats MM/DD/YYYY or DD/MM/YYYY
    if '/' in s:
        parts = [p.strip() for p in s.split('/')]
        if len(parts) >= 3:
            p1, p2, p3_raw = parts[0], parts[1], parts[2].split()[0]
            if len(p3_raw) == 4 and p3_raw.isdigit():
                year = int(p3_raw)
                val1, val2 = int(p1), int(p2)
                if val1 > 12:  # DD/MM/YYYY
                    try:
                        return date(year, val2, val1)
                    except ValueError:
                        pass
                else:  # MM/DD/YYYY default
                    try:
                        return date(year, val1, val2)
                    except ValueError:
                        pass
            elif len(p1) == 4 and p1.isdigit():
                try:
                    return date(int(p1), int(p2), int(p3_raw))
                except ValueError:
                    pass

    # 6. Fallback strptime standard formats
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y', '%b %d, %Y', '%d-%B-%Y', '%B %d, %Y'):
        try:
            return datetime.strptime(s.split()[0], fmt).date()
        except Exception:
            pass

    return date.today()


def clean_amount(val: Any) -> float:
    """Clean and convert string/numeric values into float amount."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float, Decimal)):
        return float(val)

    s = str(val).strip()
    if not s:
        return 0.0

    is_neg = False
    if s.startswith('(') and s.endswith(')'):
        is_neg = True
        s = s[1:-1]
    elif s.startswith('-'):
        is_neg = True
        s = s[1:]
    elif s.endswith('-'):
        is_neg = True
        s = s[:-1]

    s = re.sub(r'[^\d.]', '', s)
    if not s:
        return 0.0

    try:
        amt = float(s)
        return -amt if is_neg else amt
    except ValueError:
        return 0.0


def extract_check_number(text: Optional[str]) -> Optional[str]:
    """Attempt to extract check number from payee or memo string using regex."""
    if not text:
        return None
    
    # 1. Matches "CHECK #1001", "CHK 1001", "CK# 1001", "CHECK: 1001", "CHK-1001"
    m1 = re.search(r'(?:CHECK|CHK|CK|CHECK\s*#|CHK\s*#|CK\s*#)\s*[:#-]?\s*(\d{3,10})', text, re.IGNORECASE)
    if m1:
        return m1.group(1)

    # 2. Matches "#1001" or "# 1001"
    m2 = re.search(r'#\s*(\d{4,10})\b', text)
    if m2:
        return m2.group(1)

    return None


class BankStatementParser:
    """Service to parse OFX, QFX, and CSV bank statement files into structured objects."""

    def parse(
        self,
        file_content: Union[str, bytes],
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> ParsedStatement:
        """
        Parse statement file content (str or bytes). Automatically detects file type if not specified.
        """
        if isinstance(file_content, bytes):
            try:
                content_str = file_content.decode('utf-8')
            except UnicodeDecodeError:
                content_str = file_content.decode('latin-1', errors='replace')
        else:
            content_str = file_content or ""

        content_str = content_str.strip()

        # Determine file type
        detected_type = (file_type or "").upper()
        if not detected_type:
            if file_name:
                ext = file_name.lower().split('.')[-1]
                if ext in ('ofx', 'qfx'):
                    detected_type = 'OFX'
                elif ext == 'csv':
                    detected_type = 'CSV'

        if not detected_type:
            if '<OFX' in content_str.upper() or '<STMTTRN>' in content_str.upper() or '<BANKID>' in content_str.upper():
                detected_type = 'OFX'
            else:
                detected_type = 'CSV'

        if detected_type in ('OFX', 'QFX'):
            return self.parse_ofx(content_str, file_name=file_name)
        else:
            return self.parse_csv(content_str, file_name=file_name)

    def parse_ofx(self, content: str, file_name: Optional[str] = None) -> ParsedStatement:
        """
        Parse OFX 1.x SGML and OFX 2.x XML bank statement formats.
        """
        statement = ParsedStatement(file_name=file_name, file_type='OFX')
        if not content:
            return statement

        # Extract Bank Name / Org / FID
        org_match = re.search(r'<(?:ORG|BANKID|FID)>\s*([^<\r\n]+)', content, re.IGNORECASE)
        if org_match:
            statement.bank_name = org_match.group(1).strip()

        # Extract Account Number
        acct_match = re.search(r'<ACCTID>\s*([^<\r\n]+)', content, re.IGNORECASE)
        if acct_match:
            statement.account_number = acct_match.group(1).strip()

        # Extract Statement Balances and Dates
        bal_match = re.search(r'<BALAMT>\s*([^<\r\n]+)', content, re.IGNORECASE)
        if bal_match:
            statement.closing_balance = clean_amount(bal_match.group(1))

        asof_match = re.search(r'<DTASOF>\s*([^<\r\n]+)', content, re.IGNORECASE)
        if asof_match:
            statement.statement_date = parse_date_str(asof_match.group(1))

        start_match = re.search(r'<DTSTART>\s*([^<\r\n]+)', content, re.IGNORECASE)
        if start_match:
            statement.start_date = parse_date_str(start_match.group(1))

        end_match = re.search(r'<DTEND>\s*([^<\r\n]+)', content, re.IGNORECASE)
        if end_match:
            statement.end_date = parse_date_str(end_match.group(1))

        # Extract Transactions (<STMTTRN> blocks)
        trn_blocks = re.findall(
            r'<STMTTRN>(.*?)(?=</STMTTRN>|<STMTTRN>|</BANKTRANLIST>|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        transactions: List[ParsedTransaction] = []
        total_dep = 0.0
        total_with = 0.0

        for block in trn_blocks:
            type_m = re.search(r'<TRNTYPE>\s*([^<\r\n]+)', block, re.IGNORECASE)
            raw_type = type_m.group(1).strip().upper() if type_m else 'CHECK'

            dt_m = re.search(r'<DTPOSTED>\s*([^<\r\n]+)', block, re.IGNORECASE)
            tx_date = parse_date_str(dt_m.group(1)) if dt_m else statement.statement_date

            amt_m = re.search(r'<TRNAMT>\s*([^<\r\n]+)', block, re.IGNORECASE)
            amt = clean_amount(amt_m.group(1)) if amt_m else 0.0

            fit_m = re.search(r'<FITID>\s*([^<\r\n]+)', block, re.IGNORECASE)
            fit_id = fit_m.group(1).strip() if fit_m else None

            chk_m = re.search(r'<(?:CHECKNUM|CHKNUM)>\s*([^<\r\n]+)', block, re.IGNORECASE)
            check_num = chk_m.group(1).strip() if chk_m else None

            name_m = re.search(r'<(?:NAME|PAYEE)>\s*([^<\r\n]+)', block, re.IGNORECASE)
            payee_name = name_m.group(1).strip() if name_m else None

            memo_m = re.search(r'<MEMO>\s*([^<\r\n]+)', block, re.IGNORECASE)
            memo = memo_m.group(1).strip() if memo_m else None

            # Fallback check number extraction from memo / name
            if not check_num:
                check_num = extract_check_number(memo) or extract_check_number(payee_name)

            # Categorize transaction type
            if check_num or raw_type == 'CHECK':
                tx_type = 'CHECK'
            elif amt > 0:
                tx_type = 'DEPOSIT'
            else:
                tx_type = 'WITHDRAWAL'

            if amt > 0:
                total_dep += amt
            else:
                total_with += abs(amt)

            transactions.append(ParsedTransaction(
                transaction_date=tx_date,
                amount=amt,
                fit_id=fit_id,
                check_number=check_num,
                payee_name=payee_name,
                memo=memo,
                transaction_type=tx_type,
                match_status='Pending',
            ))

        statement.transactions = transactions
        statement.total_transactions = len(transactions)
        statement.total_deposits = round(total_dep, 2)
        statement.total_withdrawals = round(total_with, 2)

        if transactions:
            if not statement.start_date:
                statement.start_date = min(t.transaction_date for t in transactions)
            if not statement.end_date:
                statement.end_date = max(t.transaction_date for t in transactions)

        return statement

    def parse_csv(self, content: str, file_name: Optional[str] = None) -> ParsedStatement:
        """
        Parse CSV bank statement format with header identification and flexible column matching.
        """
        statement = ParsedStatement(file_name=file_name, file_type='CSV')
        if not content:
            return statement

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return statement

        # Scan for metadata lines in prefix
        header_idx = -1
        for idx, line in enumerate(lines[:15]):
            line_lower = line.lower()
            if 'bank' in line_lower and ':' in line:
                statement.bank_name = line.split(':', 1)[1].strip()
            elif 'account' in line_lower and ':' in line:
                statement.account_number = line.split(':', 1)[1].strip()

            # Check if line looks like CSV header
            if any(kw in line_lower for kw in ('date', 'amount', 'payee', 'description', 'check', 'deposit', 'debit')):
                header_idx = idx
                break

        if header_idx == -1:
            header_idx = 0

        header_line = lines[header_idx]
        csv_reader = csv.reader(lines[header_idx:])
        header_cols = [c.strip().lower() for c in next(csv_reader)]

        # Map column indices
        date_col = -1
        check_col = -1
        payee_col = -1
        memo_col = -1
        amt_col = -1
        dep_col = -1
        with_col = -1
        type_col = -1
        fit_col = -1

        for idx, col in enumerate(header_cols):
            if date_col == -1 and re.search(r'date|dtposted|time|post', col):
                date_col = idx
            elif check_col == -1 and re.search(r'check|chk|ck\s*#|ref\s*num|reference', col):
                check_col = idx
            elif payee_col == -1 and re.search(r'payee|description|desc|name|vendor|party', col):
                payee_col = idx
            elif memo_col == -1 and re.search(r'memo|notes|detail', col):
                memo_col = idx
            elif type_col == -1 and re.search(r'type|trn_type|transaction_type', col):
                type_col = idx
            elif fit_col == -1 and re.search(r'fitid|fit_id|trans_id|transaction_id|id', col):
                fit_col = idx
            elif amt_col == -1 and re.search(r'^amount$|^amt$|val|transaction\s*amount', col):
                amt_col = idx
            elif dep_col == -1 and re.search(r'deposit|credit|cash\s*in', col):
                dep_col = idx
            elif with_col == -1 and re.search(r'withdrawal|debit|paid\s*out|cash\s*out', col):
                with_col = idx

        # Fallbacks for columns if not detected
        if date_col == -1:
            date_col = 0
        if payee_col == -1 and len(header_cols) > 1:
            payee_col = 1

        transactions: List[ParsedTransaction] = []
        total_dep = 0.0
        total_with = 0.0

        for row in csv_reader:
            if not row or all(not cell.strip() for cell in row):
                continue

            tx_date = parse_date_str(row[date_col]) if date_col < len(row) else date.today()
            check_num = row[check_col].strip() if check_col != -1 and check_col < len(row) and row[check_col].strip() else None
            payee_name = row[payee_col].strip() if payee_col != -1 and payee_col < len(row) and row[payee_col].strip() else None
            memo = row[memo_col].strip() if memo_col != -1 and memo_col < len(row) and row[memo_col].strip() else None
            fit_id = row[fit_col].strip() if fit_col != -1 and fit_col < len(row) and row[fit_col].strip() else None
            raw_type = row[type_col].strip().upper() if type_col != -1 and type_col < len(row) and row[type_col].strip() else None

            # Calculate amount
            amt = 0.0
            if amt_col != -1 and amt_col < len(row):
                amt = clean_amount(row[amt_col])
            else:
                dep_val = clean_amount(row[dep_col]) if dep_col != -1 and dep_col < len(row) else 0.0
                with_val = clean_amount(row[with_col]) if with_col != -1 and with_col < len(row) else 0.0
                if dep_val != 0.0:
                    amt = abs(dep_val)
                elif with_val != 0.0:
                    amt = -abs(with_val)

            # Check number fallback extraction
            if not check_num:
                check_num = extract_check_number(memo) or extract_check_number(payee_name)

            if check_num or raw_type == 'CHECK':
                tx_type = 'CHECK'
            elif amt > 0:
                tx_type = 'DEPOSIT'
            else:
                tx_type = 'WITHDRAWAL'

            if amt > 0:
                total_dep += amt
            else:
                total_with += abs(amt)

            transactions.append(ParsedTransaction(
                transaction_date=tx_date,
                amount=amt,
                fit_id=fit_id,
                check_number=check_num,
                payee_name=payee_name,
                memo=memo,
                transaction_type=tx_type,
                match_status='Pending',
            ))

        statement.transactions = transactions
        statement.total_transactions = len(transactions)
        statement.total_deposits = round(total_dep, 2)
        statement.total_withdrawals = round(total_with, 2)

        if transactions:
            if not statement.start_date:
                statement.start_date = min(t.transaction_date for t in transactions)
            if not statement.end_date:
                statement.end_date = max(t.transaction_date for t in transactions)

        return statement


bank_statement_parser = BankStatementParser()

__all__ = [
    'ParsedTransaction',
    'ParsedStatement',
    'BankStatementParser',
    'bank_statement_parser',
    'parse_date_str',
    'clean_amount',
    'extract_check_number',
]
