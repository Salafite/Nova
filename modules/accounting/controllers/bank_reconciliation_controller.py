from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body
from pydantic import BaseModel, Field

from modules.accounting.services.bank_statement_parser import BankStatementParser
from modules.accounting.services.check_matching_service import CheckMatchingService
from modules.accounting.services.check_clearing_service import CheckClearingService
from modules.accounting.models.check_clearing import (
    BANK_STATEMENT_REPO,
    STATEMENT_TRANSACTION_REPO,
    CHECK_CLEARING_RECORD_REPO,
)

router = APIRouter(prefix="/api/bank-reconciliation", tags=["Bank Statement Reconciliation & Check Clearing"])

matching_service = CheckMatchingService()
clearing_service = CheckClearingService()


class StatementUploadRequest(BaseModel):
    file_content: str = Field(..., description="Raw text or base64 decoded string of statement file")
    file_name: str = Field("statement.ofx", description="Original file name")
    file_type: Optional[str] = Field(None, description="OFX or CSV (auto-detected if null)")


class ManualMatchRequest(BaseModel):
    statement_transaction_id: int
    payment_id: int


class BatchClearRequest(BaseModel):
    statement_id: int
    transaction_ids: Optional[List[int]] = Field(None, description="Specific transaction IDs to clear (or null for all matched)")


@router.post("/upload")
async def upload_bank_statement(
    file: Optional[UploadFile] = File(None),
    payload: Optional[StatementUploadRequest] = Body(None),
):
    """
    Upload a bank statement file (OFX or CSV), parse transaction lines,
    store statement records, and run auto-matching against pending customer checks.
    """
    try:
        content_str = ""
        file_name = "statement.ofx"
        file_type = None

        if file:
            file_bytes = await file.read()
            content_str = file_bytes.decode('utf-8', errors='replace')
            file_name = file.filename or "statement.ofx"
        elif payload:
            content_str = payload.file_content
            file_name = payload.file_name
            file_type = payload.file_type
        else:
            raise HTTPException(400, "Must provide either a file upload or JSON file_content payload")

        if not content_str.strip():
            raise HTTPException(400, "Uploaded file content is empty")

        parsed = BankStatementParser.parse(content_str, file_name=file_name, file_type=file_type)

        # Create Bank Statement Record (t0108)
        stmt_dict = parsed.to_dict()
        txns_list = stmt_dict.pop('transactions', [])

        stmt_rec = BANK_STATEMENT_REPO.create(stmt_dict)
        stmt_id = stmt_rec['id']

        # Create Statement Transactions (t0109)
        created_txns = []
        for txn in txns_list:
            txn['statement_id'] = stmt_id
            t_rec = STATEMENT_TRANSACTION_REPO.create(txn)
            created_txns.append(t_rec)

        # Execute Auto-matching Engine
        match_result = matching_service.match_statement_transactions(stmt_id)

        # Refetch updated statement header
        updated_stmt = BANK_STATEMENT_REPO.get(stmt_id)

        return {
            'message': 'Bank statement processed successfully',
            'statement': updated_stmt,
            'match_summary': match_result,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to upload bank statement: {e}")


@router.get("/statements")
def list_bank_statements(
    status: Optional[str] = Query(None, description="Filter by status (Uploaded, Matched, Reconciled)"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
):
    """
    Retrieve list of uploaded bank statements.
    """
    filters = {}
    if status:
        filters['status'] = status
    if bank_name:
        filters['bank_name'] = bank_name

    statements = BANK_STATEMENT_REPO.list(filters=filters if filters else None)
    return statements


@router.get("/statements/{statement_id}")
def get_bank_statement_details(statement_id: int):
    """
    Retrieve bank statement header details and all associated transaction lines with match info.
    """
    statement = BANK_STATEMENT_REPO.get(statement_id)
    if not statement:
        raise HTTPException(404, f"Bank statement {statement_id} not found")

    transactions = STATEMENT_TRANSACTION_REPO.list(filters={'statement_id': statement_id})
    return {
        'statement': statement,
        'transactions': transactions,
    }


@router.post("/statements/{statement_id}/match")
def auto_match_statement_checks(
    statement_id: int,
    date_tolerance_days: int = Query(30, description="Tolerance days for check date matching"),
    min_score_threshold: float = Query(0.70, description="Minimum confidence score threshold"),
):
    """
    Trigger auto-matching algorithm on pending statement transactions for a statement.
    """
    try:
        result = matching_service.match_statement_transactions(
            statement_id=statement_id,
            date_tolerance_days=date_tolerance_days,
            min_score_threshold=min_score_threshold,
        )
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Auto-matching failed: {e}")


@router.post("/match/manual")
def manual_match_check(req: ManualMatchRequest):
    """
    Manually associate a bank statement transaction line with an ERP pending check payment.
    """
    try:
        result = matching_service.manual_match(
            statement_transaction_id=req.statement_transaction_id,
            payment_id=req.payment_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Manual match failed: {e}")


@router.post("/statements/{statement_id}/clear-batch")
@router.post("/clear-batch")
def confirm_batch_check_clearing(
    statement_id: Optional[int] = None,
    payload: Optional[BatchClearRequest] = Body(None),
):
    """
    1-Click confirm matched checks batch: updates payment statuses to Cleared,
    updates check clearing records, and creates General Ledger journal entries.
    """
    try:
        target_stmt_id = statement_id or (payload.statement_id if payload else None)
        if not target_stmt_id:
            raise HTTPException(400, "statement_id must be provided in path or JSON body")

        txn_ids = payload.transaction_ids if payload else None

        result = clearing_service.clear_matched_checks_batch(
            statement_id=target_stmt_id,
            transaction_ids=txn_ids,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Batch clearing failed: {e}")
