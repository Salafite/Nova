"""
Unit tests for BankStatementParser service (OFX/QFX and CSV bank statement parsing).
"""

from datetime import date
import pytest
from modules.accounting.services.bank_statement_parser import (
    BankStatementParser,
    bank_statement_parser,
    ParsedStatement,
    ParsedTransaction,
    clean_amount,
    extract_check_number,
    parse_date_str,
)


def test_clean_amount():
    assert clean_amount("1500.50") == 1500.50
    assert clean_amount("-1500.50") == -1500.50
    assert clean_amount("(1,500.50)") == -1500.50
    assert clean_amount("$2,450.00") == 2450.00
    assert clean_amount(None) == 0.0


def test_extract_check_number():
    assert extract_check_number("Payment for invoice CHK 1004") == "1004"
    assert extract_check_number("CHECK #8821 DISTRIBUTOR INC") == "8821"
    assert extract_check_number("CK: 5044") == "5044"
    assert extract_check_number("Ref #99211 payment") == "99211"
    assert extract_check_number("Regular wire transfer") is None


def test_parse_date_str():
    assert parse_date_str("2026-09-01") == date(2026, 9, 1)
    assert parse_date_str("20260901120000[0:GMT]") == date(2026, 9, 1)
    assert parse_date_str("09/01/2026") == date(2026, 9, 1)
    assert parse_date_str("20260901") == date(2026, 9, 1)


def test_parse_ofx_bank_statement():
    ofx_content = """OFXHEADER:100
DATA:OFXSGML
<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKACCTFROM>
<BANKID>123456789
<ACCTID>9876543210
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101
<DTEND>20260131
<STMTTRN>
<TRNTYPE>CHECK
<DTPOSTED>20260115
<TRNAMT>-1500.50
<FITID>FIT1001
<CHECKNUM>1054
<NAME>US Foods Inc
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEP
<DTPOSTED>20260118
<TRNAMT>3250.00
<FITID>FIT1002
<NAME>Customer Payment Check #2045
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>15400.00
<DTASOF>20260131
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""

    parsed = BankStatementParser.parse_file(ofx_content.encode('utf-8'), 'statement_jan2026.ofx')

    assert parsed['bank_name'] == '123456789'
    assert parsed['account_number'] == '9876543210'
    assert parsed['closing_balance'] == 15400.00
    assert parsed['total_transactions'] == 2
    assert len(parsed['transactions']) == 2

    # Check first transaction
    t1 = parsed['transactions'][0]
    assert t1['check_number'] == '1054'
    assert t1['amount'] == -1500.50
    assert t1['transaction_date'] == date(2026, 1, 15)

    # Check second transaction (check num extracted from text)
    t2 = parsed['transactions'][1]
    assert t2['check_number'] == '2045'
    assert t2['amount'] == 3250.00


def test_parse_csv_bank_statement():
    csv_content = """Date,Check Number,Payee,Amount,FITID
2026-02-01,5001,Sysco Foods,-450.00,TXN8801
2026-02-05,5002,Metro Cash Deposit,1200.00,TXN8802
2026-02-10,,Check #6012 Received,850.25,TXN8803
"""

    parsed = BankStatementParser.parse_file(csv_content.encode('utf-8'), 'statement_feb2026.csv')

    assert parsed['file_type'] == 'CSV'
    assert parsed['total_transactions'] == 3
    assert len(parsed['transactions']) == 3

    t1 = parsed['transactions'][0]
    assert t1['check_number'] == '5001'
    assert t1['amount'] == -450.00

    t3 = parsed['transactions'][2]
    assert t3['check_number'] == '6012'
    assert t3['amount'] == 850.25


def test_parse_csv_split_deposit_withdrawal():
    csv_content = """Posting Date,Chk #,Payee Name,Deposit,Withdrawal
09/01/2026,7001,Bakery Supplies,,450.00
09/02/2026,7002,Supermarket Customer,1850.00,
"""

    statement = bank_statement_parser.parse(csv_content, file_type="CSV")

    assert statement.total_transactions == 2
    assert statement.total_deposits == 1850.00
    assert statement.total_withdrawals == 450.00

    t1 = statement.transactions[0]
    assert t1.amount == -450.00
    assert t1.check_number == "7001"

    t2 = statement.transactions[1]
    assert t2.amount == 1850.00
    assert t2.check_number == "7002"


def test_parse_bytes_input():
    content = b"Date,Check Number,Description,Amount\n2026-09-10,9901,Vendor Check,-300.00\n"
    statement = bank_statement_parser.parse(content, file_name="statement.csv")

    assert statement.total_transactions == 1
    assert statement.transactions[0].check_number == "9901"
    assert statement.transactions[0].amount == -300.00


def test_to_dict_format():
    parsed_tx = ParsedTransaction(
        transaction_date=date(2026, 9, 1),
        amount=500.0,
        check_number="1234",
    )
    tx_dict = parsed_tx.to_dict()
    assert tx_dict["transaction_date"] == date(2026, 9, 1)
    assert tx_dict["check_number"] == "1234"
    assert tx_dict["amount"] == 500.0

    parsed_stmt = ParsedStatement(
        bank_name="Test Bank",
        account_number="12345",
        transactions=[parsed_tx],
    )
    stmt_dict = parsed_stmt.to_dict()
    assert stmt_dict["bank_name"] == "Test Bank"
    assert len(stmt_dict["transactions"]) == 1
