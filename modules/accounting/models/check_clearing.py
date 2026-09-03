"""
Nova ERP — Check Clearing & Bank Statement Reconciliation Models & Repositories

Defines Pydantic schemas and CrudRepository instances for:
- Bank Statements (t0108)
- Statement Transactions (t0109)
- Check Clearing Records (t0110)
"""

from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin
from modules.core.repositories.base import CrudRepository


# ---------------------------------------------------------------------------
# Bank Statement (T0108)
# ---------------------------------------------------------------------------
class BankStatementCreate(BaseModel):
    statement_number: Optional[str] = Field(None, max_length=50)
    bank_name: str = Field(..., max_length=100)
    account_number: str = Field(..., max_length=50)
    statement_date: date = Field(default_factory=date.today)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0
    file_name: Optional[str] = Field(None, max_length=255)
    file_type: str = Field(default='OFX', max_length=20)
    status: str = Field(default='Uploaded', max_length=30)
    total_transactions: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    notes: Optional[str] = None
    is_active: bool = True
    business_id: Optional[int] = None


class BankStatementUpdate(BaseModel):
    statement_number: Optional[str] = Field(None, max_length=50)
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    statement_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_deposits: Optional[float] = None
    total_withdrawals: Optional[float] = None
    file_name: Optional[str] = Field(None, max_length=255)
    file_type: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, max_length=30)
    total_transactions: Optional[int] = None
    matched_count: Optional[int] = None
    unmatched_count: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class BankStatementResponse(AuditMixin):
    id: int
    statement_number: str
    bank_name: str
    account_number: str
    statement_date: date
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
    is_active: bool = True


# ---------------------------------------------------------------------------
# Statement Transaction (T0109)
# ---------------------------------------------------------------------------
class StatementTransactionCreate(BaseModel):
    statement_id: int
    transaction_date: date
    fit_id: Optional[str] = Field(None, max_length=100)
    check_number: Optional[str] = Field(None, max_length=50)
    payee_name: Optional[str] = Field(None, max_length=255)
    memo: Optional[str] = None
    amount: float
    transaction_type: str = Field(default='CHECK', max_length=50)
    match_status: str = Field(default='Pending', max_length=30)
    matched_payment_id: Optional[int] = None
    match_score: Optional[float] = None
    notes: Optional[str] = None
    is_active: bool = True
    business_id: Optional[int] = None


class StatementTransactionUpdate(BaseModel):
    statement_id: Optional[int] = None
    transaction_date: Optional[date] = None
    fit_id: Optional[str] = Field(None, max_length=100)
    check_number: Optional[str] = Field(None, max_length=50)
    payee_name: Optional[str] = Field(None, max_length=255)
    memo: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[str] = Field(None, max_length=50)
    match_status: Optional[str] = Field(None, max_length=30)
    matched_payment_id: Optional[int] = None
    match_score: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class StatementTransactionResponse(AuditMixin):
    id: int
    statement_id: int
    transaction_date: date
    fit_id: Optional[str] = None
    check_number: Optional[str] = None
    payee_name: Optional[str] = None
    memo: Optional[str] = None
    amount: float
    transaction_type: str = 'CHECK'
    match_status: str = 'Pending'
    matched_payment_id: Optional[int] = None
    match_score: Optional[float] = None
    notes: Optional[str] = None
    is_active: bool = True


# ---------------------------------------------------------------------------
# Check Clearing Record (T0110)
# ---------------------------------------------------------------------------
class CheckClearingRecordCreate(BaseModel):
    clearing_number: Optional[str] = Field(None, max_length=50)
    payment_id: Optional[int] = None
    statement_transaction_id: Optional[int] = None
    customer_id: Optional[int] = None
    check_number: str = Field(..., max_length=50)
    bank_name: Optional[str] = Field(None, max_length=100)
    payee_payer: Optional[str] = Field(None, max_length=255)
    amount: float
    issue_date: Optional[date] = None
    clearing_date: Optional[date] = None
    status: str = Field(default='Pending', max_length=30)
    bounced_date: Optional[date] = None
    bounced_reason: Optional[str] = None
    penalty_fee: float = 0.0
    credit_hold_triggered: bool = False
    notes: Optional[str] = None
    is_active: bool = True
    business_id: Optional[int] = None


class CheckClearingRecordUpdate(BaseModel):
    clearing_number: Optional[str] = Field(None, max_length=50)
    payment_id: Optional[int] = None
    statement_transaction_id: Optional[int] = None
    customer_id: Optional[int] = None
    check_number: Optional[str] = Field(None, max_length=50)
    bank_name: Optional[str] = Field(None, max_length=100)
    payee_payer: Optional[str] = Field(None, max_length=255)
    amount: Optional[float] = None
    issue_date: Optional[date] = None
    clearing_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=30)
    bounced_date: Optional[date] = None
    bounced_reason: Optional[str] = None
    penalty_fee: Optional[float] = None
    credit_hold_triggered: Optional[bool] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CheckClearingRecordResponse(AuditMixin):
    id: int
    clearing_number: str
    payment_id: Optional[int] = None
    statement_transaction_id: Optional[int] = None
    customer_id: Optional[int] = None
    check_number: str
    bank_name: Optional[str] = None
    payee_payer: Optional[str] = None
    amount: float
    issue_date: Optional[date] = None
    clearing_date: Optional[date] = None
    status: str = 'Pending'
    bounced_date: Optional[date] = None
    bounced_reason: Optional[str] = None
    penalty_fee: float = 0.0
    credit_hold_triggered: bool = False
    notes: Optional[str] = None
    is_active: bool = True


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------
BANK_STATEMENT_REPO = CrudRepository(
    'T0108',
    business_columns=[
        'id',
        'statement_number',
        'bank_name',
        'account_number',
        'statement_date',
        'start_date',
        'end_date',
        'opening_balance',
        'closing_balance',
        'total_deposits',
        'total_withdrawals',
        'file_name',
        'file_type',
        'status',
        'total_transactions',
        'matched_count',
        'unmatched_count',
        'notes',
        'is_active',
    ],
)

STATEMENT_TRANSACTION_REPO = CrudRepository(
    'T0109',
    business_columns=[
        'id',
        'statement_id',
        'transaction_date',
        'fit_id',
        'check_number',
        'payee_name',
        'memo',
        'amount',
        'transaction_type',
        'match_status',
        'matched_payment_id',
        'match_score',
        'notes',
        'is_active',
    ],
)

CHECK_CLEARING_RECORD_REPO = CrudRepository(
    'T0110',
    business_columns=[
        'id',
        'clearing_number',
        'payment_id',
        'statement_transaction_id',
        'customer_id',
        'check_number',
        'bank_name',
        'payee_payer',
        'amount',
        'issue_date',
        'clearing_date',
        'status',
        'bounced_date',
        'bounced_reason',
        'penalty_fee',
        'credit_hold_triggered',
        'notes',
        'is_active',
    ],
)
