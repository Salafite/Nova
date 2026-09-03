import pytest
from datetime import date
from modules.accounting.services.bank_statement_parser import BankStatementParser


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
