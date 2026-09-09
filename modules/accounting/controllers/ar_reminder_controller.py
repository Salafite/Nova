"""
AR Reminders & Statement Configuration REST Controller for Nova ERP.

Exposes endpoints for:
- AR Reminder Rules CRUD (/api/accounting/reminder-rules)
- AR Reminder Templates CRUD (/api/accounting/reminder-templates)
- Manual On-Demand Reminder Dispatch (/api/accounting/reminders/dispatch)
- Manual On-Demand Statement Dispatch (/api/accounting/reminders/dispatch-statement)
- Batch Reminder Evaluation Engine (/api/accounting/reminders/run-batch)
- Downloadable/Streamable Customer Statement PDF (/api/accounting/customers/{customer_id}/statement-pdf)
- Portfolio-wide AR Overdue Summary & Health Metrics (/api/accounting/reminders/summary)
- Single Customer Eligibility Evaluation Preview (/api/accounting/reminders/evaluate-eligibility)
"""

import io
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from modules.accounting.models.reminder import (
    ARReminderRuleCreate,
    ARReminderRuleUpdate,
    ARReminderRuleResponse,
    ARReminderTemplateCreate,
    ARReminderTemplateUpdate,
    ARReminderTemplateResponse,
    ReminderDispatchPayload,
    StatementDispatchPayload,
    BatchReminderRunRequest,
    BatchReminderResult,
)
from modules.accounting.services.ar_reminder_service import (
    ARReminderService,
    ar_reminder_service as default_ar_reminder_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/accounting",
    tags=["AR Reminders & Statement Dispatch"],
)

service: ARReminderService = default_ar_reminder_service


# ----------------------------------------------------------------------
# Request Models for Custom Endpoints
# ----------------------------------------------------------------------
class EligibilityEvaluationRequest(BaseModel):
    customer_id: int = Field(..., description="Customer ID (T0010)")
    rule_id: int = Field(..., description="AR Reminder Rule ID (t0120)")
    as_of_date: Optional[Union[date, str]] = Field(None, description="Evaluation date (YYYY-MM-DD)")


class StatementPdfRequest(BaseModel):
    as_of_date: Optional[Union[date, str]] = None
    start_date: Optional[Union[date, str]] = None
    end_date: Optional[Union[date, str]] = None
    payment_link: Optional[str] = None
    custom_message: Optional[str] = None
    currency: str = "USD"


# ----------------------------------------------------------------------
# 1. AR Reminder Rules Endpoints (/api/accounting/reminder-rules)
# ----------------------------------------------------------------------
@router.get("/reminder-rules")
def list_reminder_rules(
    is_active: Optional[bool] = Query(None, description="Filter active/inactive rules"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type (AGING_THRESHOLD, STATEMENT_SCHEDULE, DUE_DATE_OFFSET)"),
    channel: Optional[str] = Query(None, description="Filter by channel (EMAIL, WHATSAPP, ALL)"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Record offset"),
):
    """Retrieve list of configured AR collection reminder rules with linked template names."""
    try:
        rules = service.list_rules(
            is_active=is_active,
            trigger_type=trigger_type,
            channel=channel,
            limit=limit,
            offset=offset,
        )
        return rules
    except Exception as e:
        logger.error("Error listing reminder rules: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list reminder rules: {str(e)}")


@router.post("/reminder-rules", status_code=status.HTTP_201_CREATED)
def create_reminder_rule(payload: ARReminderRuleCreate):
    """Create a new AR collection reminder rule with aging thresholds and schedule configuration."""
    try:
        created = service.create_rule(payload)
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating reminder rule: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create reminder rule: {str(e)}")


@router.get("/reminder-rules/{id}")
def get_reminder_rule(id: int = Path(..., description="Reminder Rule ID")):
    """Get details of a specific AR reminder rule by ID."""
    rule = service.get_rule(id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Reminder rule with ID {id} was not found")
    return rule


@router.put("/reminder-rules/{id}")
def update_reminder_rule(id: int = Path(..., description="Reminder Rule ID"), payload: ARReminderRuleUpdate = Body(...)):
    """Update an existing AR reminder rule."""
    existing = service.get_rule(id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Reminder rule with ID {id} was not found")
    try:
        updated = service.update_rule(id, payload)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating reminder rule %s: %s", id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update reminder rule: {str(e)}")


@router.delete("/reminder-rules/{id}")
def delete_reminder_rule(id: int = Path(..., description="Reminder Rule ID")):
    """Delete or deactivate an AR reminder rule."""
    existing = service.get_rule(id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Reminder rule with ID {id} was not found")
    try:
        success = service.delete_rule(id)
        return {"success": success, "message": f"Reminder rule {id} deleted successfully"}
    except Exception as e:
        logger.error("Error deleting reminder rule %s: %s", id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder rule: {str(e)}")


# ----------------------------------------------------------------------
# 2. AR Reminder Templates Endpoints (/api/accounting/reminder-templates)
# ----------------------------------------------------------------------
@router.get("/reminder-templates")
def list_reminder_templates(
    channel: Optional[str] = Query(None, description="Filter by channel (EMAIL, WHATSAPP)"),
    is_active: Optional[bool] = Query(None, description="Filter active/inactive templates"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Record offset"),
):
    """Retrieve list of customizable email and WhatsApp reminder message templates."""
    try:
        templates = service.list_templates(
            channel=channel,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
        return templates
    except Exception as e:
        logger.error("Error listing reminder templates: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list reminder templates: {str(e)}")


@router.post("/reminder-templates", status_code=status.HTTP_201_CREATED)
def create_reminder_template(payload: ARReminderTemplateCreate):
    """Create a new message template for AR collection reminders."""
    try:
        created = service.create_template(payload)
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating reminder template: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create reminder template: {str(e)}")


@router.get("/reminder-templates/{id}")
def get_reminder_template(id: int = Path(..., description="Template ID")):
    """Get details of a specific AR reminder template by ID."""
    template = service.get_template(id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Reminder template with ID {id} was not found")
    return template


@router.put("/reminder-templates/{id}")
def update_reminder_template(id: int = Path(..., description="Template ID"), payload: ARReminderTemplateUpdate = Body(...)):
    """Update an existing AR reminder template."""
    existing = service.get_template(id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Reminder template with ID {id} was not found")
    try:
        updated = service.update_template(id, payload)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating reminder template %s: %s", id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update reminder template: {str(e)}")


@router.delete("/reminder-templates/{id}")
def delete_reminder_template(id: int = Path(..., description="Template ID")):
    """Delete or deactivate an AR reminder template."""
    existing = service.get_template(id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Reminder template with ID {id} was not found")
    try:
        success = service.delete_template(id)
        return {"success": success, "message": f"Reminder template {id} deleted successfully"}
    except Exception as e:
        logger.error("Error deleting reminder template %s: %s", id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder template: {str(e)}")


# ----------------------------------------------------------------------
# 3. Manual On-Demand Reminder & Statement Dispatch
# ----------------------------------------------------------------------
@router.post("/reminders/dispatch")
def dispatch_manual_reminder(payload: ReminderDispatchPayload):
    """
    Manually dispatch an overdue payment reminder to a customer via WhatsApp, Email, or both.
    Optionally attaches an account statement PDF and payment link.
    """
    try:
        result = service.send_customer_reminder(
            customer_id=payload.customer_id,
            rule_id=payload.rule_id,
            template_id=payload.template_id,
            channel=payload.channel,
            custom_message=payload.custom_message,
            attach_statement_pdf=payload.attach_statement_pdf,
            include_payment_link=payload.include_payment_link,
            recipient_email=payload.recipient_email,
            recipient_phone=payload.recipient_phone,
            business_id=payload.business_id,
        )
        return result
    except ValueError as e:
        err_str = str(e)
        if "not found" in err_str.lower():
            raise HTTPException(status_code=404, detail=err_str)
        raise HTTPException(status_code=400, detail=err_str)
    except Exception as e:
        logger.error("Error dispatching manual reminder for customer %s: %s", payload.customer_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to dispatch reminder: {str(e)}")


@router.post("/reminders/dispatch-statement")
@router.post("/statements/dispatch")
def dispatch_customer_statement(payload: StatementDispatchPayload):
    """
    Generate and dispatch a branded customer account statement PDF via Email or WhatsApp.
    """
    try:
        result = service.dispatch_customer_statement(
            customer_id=payload.customer_id,
            channel=payload.channel,
            start_date=payload.start_date,
            end_date=payload.end_date,
            as_of_date=payload.as_of_date,
            custom_message=payload.custom_message,
            recipient_email=payload.recipient_email,
            recipient_phone=payload.recipient_phone,
            business_id=payload.business_id,
        )
        return result
    except ValueError as e:
        err_str = str(e)
        if "not found" in err_str.lower():
            raise HTTPException(status_code=404, detail=err_str)
        raise HTTPException(status_code=400, detail=err_str)
    except Exception as e:
        logger.error("Error dispatching statement for customer %s: %s", payload.customer_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to dispatch statement: {str(e)}")


# ----------------------------------------------------------------------
# 4. Batch Reminder Engine Evaluation & Execution
# ----------------------------------------------------------------------
@router.post("/reminders/run-batch")
@router.post("/reminders/batch")
def run_batch_reminders(payload: BatchReminderRunRequest):
    """
    Execute automated batch reminder evaluation across active customer accounts.
    Supports dry_run=True for previewing candidate accounts and expected dispatch channels.
    """
    try:
        result = service.run_batch_reminders(
            rule_id=payload.rule_id,
            customer_ids=payload.customer_ids,
            as_of_date=payload.as_of_date,
            dry_run=payload.dry_run,
            force=payload.force,
            business_id=payload.business_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error running batch reminders: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch reminder execution failed: {str(e)}")


# ----------------------------------------------------------------------
# 5. Customer Statement PDF Generation & Streaming
# ----------------------------------------------------------------------
@router.get("/customers/{customer_id}/statement-pdf")
@router.get("/customers/{customer_id}/statement.pdf")
def get_customer_statement_pdf(
    customer_id: int = Path(..., description="Customer ID"),
    as_of_date: Optional[str] = Query(None, description="As of date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    payment_link: Optional[str] = Query(None, description="Custom payment URL"),
    custom_message: Optional[str] = Query(None, description="Custom statement note"),
    currency: str = Query("USD", description="Currency code"),
):
    """
    Generate and stream a branded PDF account statement for a customer.
    Includes open invoice details, 5-bucket aging breakdown, and payment instructions.
    """
    customer = service.customer_repo.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with ID {customer_id} was not found")

    try:
        pdf_bytes = service.statement_pdf_service.generate_statement_pdf_for_customer(
            customer_id=customer_id,
            as_of_date=as_of_date,
            start_date=start_date,
            end_date=end_date,
            payment_link=payment_link,
            custom_message=custom_message,
            currency=currency,
        )

        date_tag = as_of_date or datetime.now().strftime("%Y%m%d")
        filename = f"statement_customer_{customer_id}_{date_tag}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Type": "application/pdf",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error generating statement PDF for customer %s: %s", customer_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate statement PDF: {str(e)}")


@router.post("/customers/{customer_id}/statement-pdf")
def post_customer_statement_pdf(
    customer_id: int = Path(..., description="Customer ID"),
    payload: Optional[StatementPdfRequest] = Body(None),
):
    """POST endpoint to generate and stream statement PDF with body parameters."""
    req = payload or StatementPdfRequest()
    return get_customer_statement_pdf(
        customer_id=customer_id,
        as_of_date=str(req.as_of_date) if req.as_of_date else None,
        start_date=str(req.start_date) if req.start_date else None,
        end_date=str(req.end_date) if req.end_date else None,
        payment_link=req.payment_link,
        custom_message=req.custom_message,
        currency=req.currency,
    )


# ----------------------------------------------------------------------
# 6. Portfolio Overdue Summary & Eligibility Preview Helpers
# ----------------------------------------------------------------------
@router.get("/reminders/summary")
@router.get("/reminders/metrics")
def get_ar_reminders_summary(
    as_of_date: Optional[str] = Query(None, description="As of evaluation date (YYYY-MM-DD)"),
):
    """Retrieve portfolio-wide AR collection summary metrics, total overdue, and aging distribution."""
    try:
        summary = service.get_ar_overdue_summary(as_of_date=as_of_date)
        return summary
    except Exception as e:
        logger.error("Error computing AR overdue summary: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute AR overdue summary: {str(e)}")


@router.post("/reminders/evaluate-eligibility")
def evaluate_customer_eligibility(payload: EligibilityEvaluationRequest):
    """Preview whether a customer account qualifies for automated reminder dispatch under a specific rule."""
    customer = service.customer_repo.get(payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with ID {payload.customer_id} was not found")

    rule = service.get_rule(payload.rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Reminder rule with ID {payload.rule_id} was not found")

    try:
        verdict = service.evaluate_customer_eligibility(
            customer=customer,
            rule=rule,
            as_of_date=payload.as_of_date,
        )
        return verdict
    except Exception as e:
        logger.error("Error evaluating eligibility: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Eligibility evaluation failed: {str(e)}")
