import io
import re
import csv
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


def parse_date_str(date_str: Any) -> Optional[date]:
    """
    Parse various date string formats into a datetime.date object.
    Supports ISO, US (MM/DD/YYYY), OFX timestamps (YYYYMMDDHHMMSS...), etc.
    """
    if not date_str:
        return None
    if isinstance(date_str, date):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()

    clean_str = str(date_str).strip()
    if not clean_str:
        return None

    # Handle OFX timestamp format like YYYYMMDDHHMMSS[...:TZ] or YYYYMMDD
    if len(clean_str) >= 8 and clean_str[:8].isdigit():
        try:
            return date(int(clean_str[:4]), int(clean_str[4:6]), int(clean_str[6:8]))
        except ValueError:
            pass

    # Standard date formats
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y.%m.%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(clean_str, fmt).date()
        except ValueError:
            continue

    return None


parse_date = parse_date_str


def clean_amount(val: Any) -> float:
    """
    Parse numeric currency or balance string into float.
    Handles parenthesized negative values (e.g. (1,500.50)), currency symbols, and commas.
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return 0.0

    is_negative = False
    if s.startswith('(') and s.endswith(')'):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith('-'):
        is_negative = True
        s = s[1:].strip()

    # Remove currency symbols, commas, and other non-numeric chars except dot
    s = re.sub(r'[^\d.]', '', s)
    if not s:
        return 0.0

    try:
        amt = float(s)
        return -amt if is_negative else amt
    except ValueError:
        return 0.0


parse_amount = clean_amount


def extract_check_number(text: Optional[str]) -> Optional[str]:
    """
    Extract check number from description, payee, or memo text if check_number field is missing.
    Matches patterns like 'CHK 1004', 'CHECK #8821', 'CK: 5044', 'Ref #99211', '#12345'.
    """
    if not text:
        return None

    # Pattern 1: 'CHECK #1234', 'CHK 1234', 'CK: 5044', 'CK 5044'
    match = re.search(r'(?:check|chk|ck[:\s]*)\s*#?\s*([0-9]+)', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: 'Ref #99211', 'Ref#99211'
    match_ref = re.search(r'ref\s*#?\s*([0-9]{3,})', text, re.IGNORECASE)
    if match_ref:
        return match_ref.group(1)

    # Pattern 3: '#12345' (3+ digits)
    match_hash = re.search(r'#([0-9]{3,})', text)
    if match_hash:
        return match_hash.group(1)

    return None


@dataclass
class ParsedTransaction:
    transaction_date: Optional[date] = None
    fit_id: Optional[str] = None
    check_number: Optional[str] = None
    payee_name: Optional[str] = None
    memo: Optional[str] = None
    amount: float = 0.0
    transaction_type: str = 'CHECK'
    match_status: str = 'Pending'

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'transaction_date': self.transaction_date,
            'fit_id': self.fit_id,
            'check_number': self.check_number,
            'payee_name': self.payee_name,
            'memo': self.memo,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'match_status': self.match_status,
        }


@dataclass
class ParsedStatement:
    statement_number: Optional[str] = None
    bank_name: str = 'Unknown Bank'
    account_number: str = 'Unknown Account'
    statement_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0
    file_name: Optional[str] = None
    file_type: str = 'OFX'
    status: str = 'Uploaded'
    total_transactions: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    notes: Optional[str] = None
    transactions: List[ParsedTransaction] = field(default_factory=list)

    def __getitem__(self, item: str) -> Any:
        if item == 'transactions':
            return [t.to_dict() if isinstance(t, ParsedTransaction) else t for t in self.transactions]
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except (AttributeError, KeyError):
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            'statement_number': self.statement_number,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'statement_date': self.statement_date,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'opening_balance': self.opening_balance,
            'closing_balance': self.closing_balance,
            'total_deposits': self.total_deposits,
            'total_withdrawals': self.total_withdrawals,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'status': self.status,
            'total_transactions': self.total_transactions,
            'matched_count': self.matched_count,
            'unmatched_count': self.unmatched_count,
            'notes': self.notes,
            'transactions': [t.to_dict() if isinstance(t, ParsedTransaction) else t for t in self.transactions],
        }


class BankStatementParser:
    """
    Parser for OFX (Open Financial Exchange) and CSV bank statement files into
    standardized statement header and transaction dictionary structures.
    """

    @classmethod
    def parse(
        cls,
        file_content: Union[str, bytes],
        file_name: str = '',
        file_type: Optional[str] = None
    ) -> ParsedStatement:
        """
        Parse a bank statement file (OFX or CSV) and return a ParsedStatement object.
        """
        if isinstance(file_content, bytes):
            content_str = file_content.decode('utf-8', errors='replace')
        else:
            content_str = file_content

        detected_type = file_type
        if not detected_type:
            name_lower = file_name.lower()
            if (
                name_lower.endswith('.ofx')
                or name_lower.endswith('.qfx')
                or '<ofx>' in content_str.lower()
                or 'ofxheader' in content_str.lower()
            ):
                detected_type = 'OFX'
            else:
                detected_type = 'CSV'

        if detected_type.upper() == 'OFX':
            return cls.parse_ofx(content_str, file_name=file_name)
        else:
            return cls.parse_csv(content_str, file_name=file_name)

    @classmethod
    def parse_file(
        cls,
        file_content: Union[str, bytes],
        file_name: str = '',
        file_type: Optional[str] = None
    ) -> ParsedStatement:
        """
        Parse statement file and return ParsedStatement (which supports both attribute and dict subscripting).
        """
        return cls.parse(file_content, file_name=file_name, file_type=file_type)

    @classmethod
    def parse_ofx(cls, content: str, file_name: str = '') -> ParsedStatement:
        """
        Parse OFX SGML/XML text content into statement header and transactions.
        """
        def get_tag_value(tag_name: str, scope: str) -> Optional[str]:
            pattern = rf'<{tag_name}>(.*?)(?:</{tag_name}>|\r?\n|<|$)'
            match = re.search(pattern, scope, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                if '<' in val:
                    val = val.split('<')[0].strip()
                return val
            return None

        bank_id = get_tag_value('BANKID', content) or 'Unknown Bank'
        acct_id = get_tag_value('ACCTID', content) or 'Unknown Account'

        ledger_bal_match = re.search(r'<LEDGERBAL>(.*?)</LEDGERBAL>', content, re.IGNORECASE | re.DOTALL)
        ledger_scope = ledger_bal_match.group(1) if ledger_bal_match else content
        bal_amt = parse_amount(get_tag_value('BALAMT', ledger_scope))
        stmt_date = parse_date_str(get_tag_value('DTASOF', ledger_scope)) or date.today()

        start_date = parse_date_str(get_tag_value('DTSTART', content))
        end_date = parse_date_str(get_tag_value('DTEND', content))

        transactions: List[ParsedTransaction] = []
        trn_matches = re.finditer(
            r'<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|(?=</BANKTRANLIST>)|$)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        for trn in trn_matches:
            block = trn.group(1)
            trn_type = get_tag_value('TRNTYPE', block) or 'CHECK'
            dt_posted = parse_date_str(get_tag_value('DTPOSTED', block)) or date.today()
            amt = parse_amount(get_tag_value('TRNAMT', block))
            fit_id = get_tag_value('FITID', block)
            check_num = get_tag_value('CHECKNUM', block)
            payee = get_tag_value('NAME', block) or get_tag_value('PAYEE', block)
            memo = get_tag_value('MEMO', block)

            if not check_num:
                check_num = extract_check_number(payee) or extract_check_number(memo)

            transactions.append(ParsedTransaction(
                transaction_date=dt_posted,
                fit_id=fit_id,
                check_number=check_num,
                payee_name=payee,
                memo=memo,
                amount=amt,
                transaction_type=trn_type,
                match_status='Pending'
            ))

        total_deposits = sum(t.amount for t in transactions if t.amount > 0)
        total_withdrawals = sum(abs(t.amount) for t in transactions if t.amount < 0)

        return ParsedStatement(
            statement_number=f"STMT-{stmt_date.strftime('%Y%m%d')}",
            bank_name=bank_id,
            account_number=acct_id,
            statement_date=stmt_date,
            start_date=start_date,
            end_date=end_date,
            opening_balance=round(bal_amt - total_deposits + total_withdrawals, 2),
            closing_balance=round(bal_amt, 2),
            total_deposits=round(total_deposits, 2),
            total_withdrawals=round(total_withdrawals, 2),
            file_name=file_name,
            file_type='OFX',
            status='Uploaded',
            total_transactions=len(transactions),
            matched_count=0,
            unmatched_count=len(transactions),
            notes=None,
            transactions=transactions
        )

    @classmethod
    def parse_csv(cls, content: str, file_name: str = '') -> ParsedStatement:
        """
        Parse CSV text content into statement header and transactions.
        """
        lines = [line for line in content.splitlines() if line.strip()]
        if not lines:
            raise ValueError("CSV file is empty")

        reader = csv.reader(lines)
        rows = list(reader)
        if not rows:
            raise ValueError("CSV file contains no data")

        header = [col.strip().lower() for col in rows[0]]

        date_idx = None
        check_idx = None
        payee_idx = None
        amount_idx = None
        fit_idx = None
        memo_idx = None
        type_idx = None
        deposit_idx = None
        withdrawal_idx = None

        for idx, col in enumerate(header):
            if col in ('date', 'transaction date', 'txn date', 'posting date', 'value date'):
                date_idx = idx
            elif col in ('check number', 'check num', 'check no', 'check #', 'chk no', 'chk #', 'check', 'ref number', 'reference'):
                check_idx = idx
            elif col in ('payee', 'payee name', 'description', 'name', 'party', 'details'):
                if payee_idx is None:
                    payee_idx = idx
            elif col in ('memo', 'notes', 'remarks'):
                memo_idx = idx
            elif col in ('amount', 'txn amount', 'net amount'):
                amount_idx = idx
            elif col in ('fitid', 'transaction id', 'txn id', 'id', 'ref id'):
                fit_idx = idx
            elif col in ('type', 'transaction type', 'txn type'):
                type_idx = idx
            elif col in ('deposit', 'credit'):
                deposit_idx = idx
            elif col in ('withdrawal', 'debit'):
                withdrawal_idx = idx

        if date_idx is None:
            date_idx = 0

        transactions: List[ParsedTransaction] = []
        for row in rows[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue

            dt_val = parse_date_str(row[date_idx]) if date_idx < len(row) else date.today()
            if not dt_val:
                dt_val = date.today()

            check_num = row[check_idx].strip() if check_idx is not None and check_idx < len(row) else None
            if check_num == '':
                check_num = None

            payee = row[payee_idx].strip() if payee_idx is not None and payee_idx < len(row) else None
            memo = row[memo_idx].strip() if memo_idx is not None and memo_idx < len(row) else None
            fit_id = row[fit_idx].strip() if fit_idx is not None and fit_idx < len(row) else None
            trn_type = row[type_idx].strip() if type_idx is not None and type_idx < len(row) else 'CHECK'

            if amount_idx is not None and amount_idx < len(row):
                amt = parse_amount(row[amount_idx])
            elif deposit_idx is not None or withdrawal_idx is not None:
                dep_amt = parse_amount(row[deposit_idx]) if deposit_idx is not None and deposit_idx < len(row) else 0.0
                wd_amt = parse_amount(row[withdrawal_idx]) if withdrawal_idx is not None and withdrawal_idx < len(row) else 0.0
                amt = dep_amt - abs(wd_amt)
            else:
                amt = 0.0

            if not check_num:
                check_num = extract_check_number(payee) or extract_check_number(memo)

            transactions.append(ParsedTransaction(
                transaction_date=dt_val,
                fit_id=fit_id,
                check_number=check_num,
                payee_name=payee,
                memo=memo,
                amount=amt,
                transaction_type=trn_type,
                match_status='Pending'
            ))

        stmt_date = max((t.transaction_date for t in transactions if t.transaction_date), default=date.today())
        total_deposits = sum(t.amount for t in transactions if t.amount > 0)
        total_withdrawals = sum(abs(t.amount) for t in transactions if t.amount < 0)

        return ParsedStatement(
            statement_number=f"STMT-CSV-{stmt_date.strftime('%Y%m%d')}",
            bank_name='Bank Statement',
            account_number='CSV Import',
            statement_date=stmt_date,
            start_date=min((t.transaction_date for t in transactions if t.transaction_date), default=stmt_date),
            end_date=stmt_date,
            opening_balance=0.0,
            closing_balance=round(total_deposits - total_withdrawals, 2),
            total_deposits=round(total_deposits, 2),
            total_withdrawals=round(total_withdrawals, 2),
            file_name=file_name,
            file_type='CSV',
            status='Uploaded',
            total_transactions=len(transactions),
            matched_count=0,
            unmatched_count=len(transactions),
            notes=None,
            transactions=transactions
        )


# Singleton / instance alias for convenience
bank_statement_parser = BankStatementParser()
