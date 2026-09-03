import csv
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import io


class BankStatementParser:
    """
    Parser service for bank statement files in OFX/QFX and CSV formats.
    Extracts statement metadata and normalized line-item transactions.
    """

    @classmethod
    def parse_file(cls, content_bytes: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parses statement content based on file extension / format.
        """
        file_ext = file_name.split('.')[-1].upper() if '.' in file_name else ''
        content_str = content_bytes.decode('utf-8', errors='replace')

        if file_ext in ['OFX', 'QFX'] or '<OFX>' in content_str.upper() or 'OFXHEADER' in content_str.upper():
            return cls.parse_ofx(content_str, file_name)
        elif file_ext == 'CSV' or ',' in content_str:
            return cls.parse_csv(content_str, file_name)
        else:
            raise ValueError(f"Unsupported file format for bank statement: {file_name}")

    @classmethod
    def parse_ofx(cls, content_str: str, file_name: str) -> Dict[str, Any]:
        """
        Parses OFX / QFX format string into structured statement data.
        """
        bank_id = cls._extract_tag(content_str, 'BANKID') or 'Unknown Bank'
        acct_id = cls._extract_tag(content_str, 'ACCTID') or 'Unknown Account'
        
        # Balances
        bal_amt_str = cls._extract_tag(content_str, 'BALAMT') or '0.00'
        try:
            closing_balance = float(bal_amt_str)
        except ValueError:
            closing_balance = 0.0

        # Dates
        dt_start_str = cls._extract_tag(content_str, 'DTSTART')
        dt_end_str = cls._extract_tag(content_str, 'DTEND')
        dt_as_of_str = cls._extract_tag(content_str, 'DTASOF')

        start_date = cls._parse_ofx_date(dt_start_str)
        end_date = cls._parse_ofx_date(dt_end_str)
        statement_date = cls._parse_ofx_date(dt_as_of_str) or end_date or date.today()

        # Transactions <STMTTRN> ... </STMTTRN> or unclosed <STMTTRN>
        trn_blocks = re.findall(r'<STMTTRN>(.*?)(?=<STMTTRN>|</STMTTRN>|</BANKTRANLIST>|$)', content_str, re.DOTALL | re.IGNORECASE)
        
        transactions: List[Dict[str, Any]] = []
        total_deposits = 0.0
        total_withdrawals = 0.0

        for block in trn_blocks:
            trn_type = (cls._extract_tag(block, 'TRNTYPE') or 'CHECK').upper()
            dt_posted_str = cls._extract_tag(block, 'DTPOSTED')
            trn_date = cls._parse_ofx_date(dt_posted_str) or statement_date
            
            amt_str = cls._extract_tag(block, 'TRNAMT') or '0.00'
            try:
                amount = float(amt_str)
            except ValueError:
                amount = 0.0

            fit_id = cls._extract_tag(block, 'FITID')
            check_num = cls._extract_tag(block, 'CHECKNUM')
            payee = cls._extract_tag(block, 'NAME') or cls._extract_tag(block, 'PAYEE')
            memo = cls._extract_tag(block, 'MEMO')

            # Extract check number from memo or payee if missing and trn_type is CHECK
            if not check_num:
                check_num = cls._extract_check_num_from_text(memo or '') or cls._extract_check_num_from_text(payee or '')

            if amount > 0:
                total_deposits += amount
            else:
                total_withdrawals += abs(amount)

            transactions.append({
                'transaction_date': trn_date,
                'fit_id': fit_id,
                'check_number': check_num,
                'payee_name': payee,
                'memo': memo,
                'amount': amount,
                'transaction_type': trn_type if trn_type else ('CHECK' if check_num else 'OTHER'),
                'match_status': 'Pending'
            })

        return {
            'bank_name': bank_id,
            'account_number': acct_id,
            'statement_date': statement_date,
            'start_date': start_date,
            'end_date': end_date,
            'opening_balance': closing_balance - total_deposits + total_withdrawals,
            'closing_balance': closing_balance,
            'total_deposits': round(total_deposits, 2),
            'total_withdrawals': round(total_withdrawals, 2),
            'file_name': file_name,
            'file_type': 'OFX' if 'OFX' in file_name.upper() else 'QFX',
            'total_transactions': len(transactions),
            'transactions': transactions
        }

    @classmethod
    def parse_csv(cls, content_str: str, file_name: str) -> Dict[str, Any]:
        """
        Parses CSV statement into structured statement data.
        """
        reader = csv.reader(io.StringIO(content_str))
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
        
        if not rows:
            raise ValueError("CSV statement file is empty")

        # Header detection
        header_index = -1
        headers = []
        for idx, row in enumerate(rows[:10]):
            row_lower = [c.strip().lower() for c in row]
            if any(h in row_lower for h in ['date', 'amount', 'check', 'check number', 'checknum', 'description', 'payee']):
                header_index = idx
                headers = row_lower
                break

        if header_index == -1:
            headers = [f'col_{i}' for i in range(len(rows[0]))]
            data_rows = rows
        else:
            data_rows = rows[header_index + 1:]

        # Map column indices
        date_idx = cls._find_col_idx(headers, ['date', 'trans date', 'posting date', 'transaction date'])
        check_idx = cls._find_col_idx(headers, ['check number', 'check num', 'check', 'chk num', 'checknum', 'ref', 'reference'])
        payee_idx = cls._find_col_idx(headers, ['payee', 'payee name', 'description', 'memo', 'name'])
        amount_idx = cls._find_col_idx(headers, ['amount', 'trans amount', 'transaction amount'])
        deposit_idx = cls._find_col_idx(headers, ['deposit', 'credit', 'amount credited'])
        withdrawal_idx = cls._find_col_idx(headers, ['withdrawal', 'debit', 'amount debited'])
        fit_idx = cls._find_col_idx(headers, ['fitid', 'transaction id', 'trans id', 'id', 'ref no'])

        transactions: List[Dict[str, Any]] = []
        total_deposits = 0.0
        total_withdrawals = 0.0
        min_date: Optional[date] = None
        max_date: Optional[date] = None

        for row in data_rows:
            if not row or all(not cell.strip() for cell in row):
                continue

            # Parse date
            raw_date = row[date_idx].strip() if date_idx is not None and date_idx < len(row) else ''
            trn_date = cls._parse_csv_date(raw_date) or date.today()

            if min_date is None or trn_date < min_date:
                min_date = trn_date
            if max_date is None or trn_date > max_date:
                max_date = trn_date

            # Parse amount
            amount = 0.0
            if amount_idx is not None and amount_idx < len(row) and row[amount_idx].strip():
                amount = cls._clean_float(row[amount_idx])
            else:
                dep = cls._clean_float(row[deposit_idx]) if deposit_idx is not None and deposit_idx < len(row) else 0.0
                wd = cls._clean_float(row[withdrawal_idx]) if withdrawal_idx is not None and withdrawal_idx < len(row) else 0.0
                if dep > 0:
                    amount = dep
                elif wd > 0:
                    amount = -wd

            if amount > 0:
                total_deposits += amount
            else:
                total_withdrawals += abs(amount)

            # Check number, payee, fitid
            check_num = row[check_idx].strip() if check_idx is not None and check_idx < len(row) else None
            payee = row[payee_idx].strip() if payee_idx is not None and payee_idx < len(row) else None
            fit_id = row[fit_idx].strip() if fit_idx is not None and fit_idx < len(row) else None

            if not check_num and payee:
                check_num = cls._extract_check_num_from_text(payee)

            transactions.append({
                'transaction_date': trn_date,
                'fit_id': fit_id,
                'check_number': check_num if check_num else None,
                'payee_name': payee,
                'memo': payee,
                'amount': amount,
                'transaction_type': 'CHECK' if check_num else ('DEPOSIT' if amount > 0 else 'WITHDRAWAL'),
                'match_status': 'Pending'
            })

        return {
            'bank_name': 'CSV Imported Bank',
            'account_number': 'CSV-ACCOUNT',
            'statement_date': max_date or date.today(),
            'start_date': min_date,
            'end_date': max_date,
            'opening_balance': 0.0,
            'closing_balance': total_deposits - total_withdrawals,
            'total_deposits': round(total_deposits, 2),
            'total_withdrawals': round(total_withdrawals, 2),
            'file_name': file_name,
            'file_type': 'CSV',
            'total_transactions': len(transactions),
            'transactions': transactions
        }

    @staticmethod
    def _extract_tag(xml_str: str, tag_name: str) -> Optional[str]:
        match = re.search(fr'<{tag_name}>(.*?)(?:</{tag_name}>|\r?\n|<)', xml_str, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _parse_ofx_date(date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        clean_str = re.sub(r'[^\d]', '', date_str)[:8]
        if len(clean_str) >= 8:
            try:
                return datetime.strptime(clean_str, '%Y%m%d').date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _parse_csv_date(date_str: str) -> Optional[date]:
        if not date_str:
            return None
        formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m-%d-%Y', '%b %d, %Y', '%d-%b-%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _clean_float(val_str: str) -> float:
        if not val_str:
            return 0.0
        cleaned = re.sub(r'[^\d\.\-]', '', val_str)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _find_col_idx(headers: List[str], candidates: List[str]) -> Optional[int]:
        for candidate in candidates:
            for idx, h in enumerate(headers):
                if candidate in h:
                    return idx
        return None

    @staticmethod
    def _extract_check_num_from_text(text: str) -> Optional[str]:
        match = re.search(r'(?:chk|check|#)\s*(\d{3,10})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
