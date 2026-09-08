"""
Customer Communication Timeline & Delivery Status Logging Service for Nova ERP.

Provides unified management of customer-facing AR and collection communication events:
- Outgoing communication logging across Email and WhatsApp channels
- Real-time delivery, read receipt, and error status updates
- Filterable and paginated customer communication timeline queries with health statistics
- Delivery failure logging, retry tracking, and automated re-dispatch execution
- Customer reminder preferences and VIP exclusion management
"""

import os
import re
import json
import uuid
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date, timezone

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.context import get_current_tenant
from modules.crm.models.customer_communication import (
    CUSTOMER_COMMUNICATION_REPO,
    CustomerCommunicationCreate,
    CustomerCommunicationUpdate,
    CustomerCommunicationResponse,
    CommunicationStatusUpdate,
    CustomerCommunicationTimelineQuery,
    CustomerReminderPreferencesUpdate,
    CustomerReminderPreferencesResponse,
)
from modules.accounting.models.reminder import (
    AR_REMINDER_RULE_REPO,
    AR_REMINDER_TEMPLATE_REPO,
)

logger = logging.getLogger(__name__)


def parse_datetime_safe(val: Any) -> Optional[datetime]:
    """Parse datetime from various formats (string, datetime, date, timestamp)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day, tzinfo=timezone.utc)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        # Replace Z with +00:00 for ISO parsing
        if val_str.endswith('Z'):
            val_str = val_str[:-1] + '+00:00'
        try:
            dt = datetime.fromisoformat(val_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


class CustomerCommunicationService(CrudService):
    """Service managing customer communication audit logs, timeline, receipts, and retries."""

    def __init__(
        self,
        communication_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        rule_repo: Optional[CrudRepository] = None,
        template_repo: Optional[CrudRepository] = None,
        dispatch_service: Optional[Any] = None,
    ):
        self.communication_repo = communication_repo or CUSTOMER_COMMUNICATION_REPO
        super().__init__(self.communication_repo)

        self.customer_repo = customer_repo or CrudRepository(
            'T0010',
            business_columns=[
                'id',
                'name',
                'group_name',
                'phone',
                'email',
                'credit_limit',
                'balance',
                'is_vip',
                'exclude_from_reminders',
                'preferred_reminder_channel',
                'reminder_phone',
                'reminder_email',
                'last_reminder_sent_at',
                'last_statement_sent_at',
                'is_active',
                'business_id',
            ],
        )
        self.rule_repo = rule_repo or AR_REMINDER_RULE_REPO
        self.template_repo = template_repo or AR_REMINDER_TEMPLATE_REPO
        self._dispatch_service = dispatch_service

    @property
    def dispatch_service(self) -> Any:
        """Lazy load ReminderDispatchService to prevent circular imports."""
        if self._dispatch_service is None:
            from modules.accounting.services.reminder_dispatch_service import reminder_dispatch_service
            self._dispatch_service = reminder_dispatch_service
        return self._dispatch_service

    # ----------------------------------------------------------------------
    # 1. Tracking Number & Helper Methods
    # ----------------------------------------------------------------------
    def generate_tracking_number(self, customer_id: Optional[int] = None, channel: str = 'COM') -> str:
        """Generate a unique tracking identifier for customer communications."""
        today_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        unique_suffix = uuid.uuid4().hex[:8].upper()
        cid = customer_id or 0
        ch = str(channel).upper()[:3]
        return f'TRK-{ch}-{today_str}-{cid}-{unique_suffix}'

    def _enhance_communication_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Attach related customer and rule metadata to a communication record."""
        if not record:
            return record

        res = dict(record)

        # Enhance customer name if missing
        if res.get('customer_id') and not res.get('customer_name'):
            try:
                cust = self.customer_repo.get(res['customer_id'])
                if cust:
                    res['customer_name'] = cust.get('name')
            except Exception:
                pass

        # Enhance rule name if missing
        if res.get('rule_id') and not res.get('rule_name'):
            try:
                rule = self.rule_repo.get(res['rule_id'])
                if rule:
                    res['rule_name'] = rule.get('rule_name')
            except Exception:
                pass

        return res

    # ----------------------------------------------------------------------
    # 2. Communication Event Recording (CRUD)
    # ----------------------------------------------------------------------
    def record_communication(
        self,
        data: Union[CustomerCommunicationCreate, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Record an outgoing communication dispatch event."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, CustomerCommunicationCreate) else dict(data)

        # Customer existence validation
        customer_id = payload.get('customer_id')
        if not customer_id:
            raise ValueError("customer_id is required to record a customer communication.")

        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} does not exist.")

        # Ensure unique tracking number
        if not payload.get('tracking_number'):
            channel = payload.get('channel', 'EMAIL')
            payload['tracking_number'] = self.generate_tracking_number(customer_id=customer_id, channel=channel)

        # Set default recipient name from customer if empty
        if not payload.get('recipient_name') and customer.get('name'):
            payload['recipient_name'] = customer.get('name')

        # Default recipient address if empty
        if not payload.get('recipient_address'):
            ch = str(payload.get('channel', 'EMAIL')).upper()
            if ch == 'EMAIL':
                payload['recipient_address'] = customer.get('reminder_email') or customer.get('email') or 'N/A'
            elif ch == 'WHATSAPP':
                payload['recipient_address'] = customer.get('reminder_phone') or customer.get('phone') or 'N/A'
            else:
                payload['recipient_address'] = 'N/A'

        # Default financial values
        if 'total_balance' not in payload:
            payload['total_balance'] = float(customer.get('balance', 0.0) or 0.0)
        if 'overdue_amount' not in payload:
            payload['overdue_amount'] = float(payload.get('total_balance', 0.0))

        # Default metadata
        if 'metadata' not in payload or payload['metadata'] is None:
            payload['metadata'] = {'retries': 0, 'retry_history': []}
        elif isinstance(payload['metadata'], dict) and 'retries' not in payload['metadata']:
            payload['metadata']['retries'] = 0
            payload['metadata']['retry_history'] = []

        created = self.communication_repo.create(payload)
        return self._enhance_communication_record(created)

    def get_communication(self, communication_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific communication log by ID with rich metadata."""
        record = self.communication_repo.get(communication_id)
        if not record:
            return None
        return self._enhance_communication_record(record)

    def get_by_tracking_number(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve a communication log by unique tracking number."""
        records = self.communication_repo.list(filters={'tracking_number': tracking_number}, limit=1)
        if not records:
            return None
        return self._enhance_communication_record(records[0])

    def get_by_external_id(self, external_message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a communication log by provider external message ID."""
        records = self.communication_repo.list(filters={'external_message_id': external_message_id}, limit=1)
        if not records:
            return None
        return self._enhance_communication_record(records[0])

    # ----------------------------------------------------------------------
    # 3. Delivery & Read Status Tracking
    # ----------------------------------------------------------------------
    def update_status(
        self,
        communication_id_or_tracking: Union[int, str],
        status_update: Union[CommunicationStatusUpdate, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update delivery or read receipt status of a communication event."""
        payload = status_update.model_dump(exclude_unset=True) if isinstance(status_update, CommunicationStatusUpdate) else dict(status_update)

        # Resolve existing record
        record = None
        if isinstance(communication_id_or_tracking, int) or str(communication_id_or_tracking).isdigit():
            record = self.communication_repo.get(int(communication_id_or_tracking))
        else:
            records = self.communication_repo.list(filters={'tracking_number': str(communication_id_or_tracking)}, limit=1)
            if records:
                record = records[0]

        if not record:
            raise ValueError(f"Communication record '{communication_id_or_tracking}' was not found.")

        record_id = record['id']
        new_status = str(payload.get('status', record.get('status', 'PENDING'))).upper()

        update_fields: Dict[str, Any] = {'status': new_status}

        if payload.get('external_message_id'):
            update_fields['external_message_id'] = payload['external_message_id']

        if payload.get('error_message') is not None:
            update_fields['error_message'] = payload['error_message']

        # Auto-populate timestamp based on status transition if not explicitly provided
        now_utc = datetime.now(timezone.utc)

        if new_status == 'DELIVERED':
            update_fields['delivery_timestamp'] = parse_datetime_safe(payload.get('delivery_timestamp')) or now_utc
        elif new_status == 'READ':
            update_fields['read_timestamp'] = parse_datetime_safe(payload.get('read_timestamp')) or now_utc
            if not record.get('delivery_timestamp'):
                update_fields['delivery_timestamp'] = update_fields['read_timestamp']
        elif new_status == 'SENT' and not record.get('delivery_timestamp'):
            if payload.get('delivery_timestamp'):
                update_fields['delivery_timestamp'] = parse_datetime_safe(payload['delivery_timestamp'])

        # Merge metadata
        if payload.get('metadata'):
            current_meta = record.get('metadata') or {}
            if isinstance(current_meta, str):
                try:
                    current_meta = json.loads(current_meta)
                except Exception:
                    current_meta = {}
            current_meta.update(payload['metadata'])
            update_fields['metadata'] = current_meta

        updated = self.communication_repo.update(record_id, update_fields)
        return self._enhance_communication_record(updated)

    def update_status_by_external_id(
        self,
        external_message_id: str,
        status: str,
        error_message: Optional[str] = None,
        timestamp: Optional[Union[datetime, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update status using external provider message ID (e.g. from webhook)."""
        record = self.get_by_external_id(external_message_id)
        if not record:
            logger.warning("No communication record found for external_message_id '%s'", external_message_id)
            return None

        update_payload: Dict[str, Any] = {
            'status': status,
            'external_message_id': external_message_id,
        }
        if error_message:
            update_payload['error_message'] = error_message
        if timestamp:
            dt = parse_datetime_safe(timestamp)
            if str(status).upper() == 'DELIVERED':
                update_payload['delivery_timestamp'] = dt
            elif str(status).upper() == 'READ':
                update_payload['read_timestamp'] = dt
        if metadata:
            update_payload['metadata'] = metadata

        return self.update_status(record['id'], update_payload)

    # ----------------------------------------------------------------------
    # 4. Customer Timeline Queries & Metrics
    # ----------------------------------------------------------------------
    def get_customer_timeline(
        self,
        customer_id: int,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        communication_type: Optional[str] = None,
        start_date: Optional[Union[datetime, date, str]] = None,
        end_date: Optional[Union[datetime, date, str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Retrieve paginated communication timeline for a specific customer with summary metrics."""
        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} was not found.")

        filters: Dict[str, Any] = {'customer_id': customer_id}
        if channel:
            filters['channel'] = str(channel).upper()
        if status:
            filters['status'] = str(status).upper()
        if communication_type:
            filters['communication_type'] = str(communication_type).upper()

        # Query all records for this customer to compute overall stats & filter by date
        all_records = self.communication_repo.list(filters={'customer_id': customer_id}, limit=1000)

        # Date range filtering & stats calculation
        start_dt = parse_datetime_safe(start_date)
        end_dt = parse_datetime_safe(end_date)
        if end_dt and isinstance(end_date, (str, date)) and not isinstance(end_date, datetime):
            # Include entire end date day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

        filtered_records: List[Dict[str, Any]] = []
        total_sent = 0
        total_delivered = 0
        total_read = 0
        total_failed = 0
        last_comm_dt = None

        for rec in all_records:
            rec_status = str(rec.get('status', 'PENDING')).upper()
            rec_ch = str(rec.get('channel', '')).upper()
            rec_type = str(rec.get('communication_type', '')).upper()
            rec_created = parse_datetime_safe(rec.get('created_at') or rec.get('delivery_timestamp'))

            # Overall stats
            if rec_status in ('SENT', 'DELIVERED', 'READ'):
                total_sent += 1
            if rec_status in ('DELIVERED', 'READ'):
                total_delivered += 1
            if rec_status == 'READ':
                total_read += 1
            if rec_status == 'FAILED':
                total_failed += 1

            if rec_created:
                if last_comm_dt is None or rec_created > last_comm_dt:
                    last_comm_dt = rec_created

            # Apply filters
            if channel and rec_ch != channel.upper():
                continue
            if status and rec_status != status.upper():
                continue
            if communication_type and rec_type != communication_type.upper():
                continue
            if start_dt and rec_created and rec_created < start_dt:
                continue
            if end_dt and rec_created and rec_created > end_dt:
                continue

            filtered_records.append(rec)

        # Sort descending by id / created_at
        filtered_records.sort(
            key=lambda x: x.get('id', 0),
            reverse=True,
        )

        total_matching = len(filtered_records)
        paged_records = filtered_records[offset: offset + limit]

        # Enhance items with rule/template names
        enhanced_items = [self._enhance_communication_record(r) for r in paged_records]

        delivery_rate = round((total_delivered / total_sent * 100.0), 1) if total_sent > 0 else 0.0
        read_rate = round((total_read / total_delivered * 100.0), 1) if total_delivered > 0 else 0.0

        return {
            'customer_id': customer_id,
            'customer_name': customer.get('name'),
            'total': total_matching,
            'limit': limit,
            'offset': offset,
            'items': enhanced_items,
            'summary': {
                'total_communications': len(all_records),
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_read': total_read,
                'total_failed': total_failed,
                'delivery_rate_percent': delivery_rate,
                'read_rate_percent': read_rate,
                'last_communication_at': last_comm_dt.isoformat() if last_comm_dt else None,
            },
        }

    def list_timeline(
        self,
        query: Optional[CustomerCommunicationTimelineQuery] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Global or multi-customer filterable communication log listing."""
        effective_filters: Dict[str, Any] = {}
        if filters:
            effective_filters.update(filters)

        start_dt = None
        end_dt = None
        eff_limit = limit
        eff_offset = offset

        if query:
            if query.customer_id:
                effective_filters['customer_id'] = query.customer_id
            if query.channel:
                effective_filters['channel'] = str(query.channel).upper()
            if query.status:
                effective_filters['status'] = str(query.status).upper()
            if query.communication_type:
                effective_filters['communication_type'] = str(query.communication_type).upper()
            if query.start_date:
                start_dt = parse_datetime_safe(query.start_date)
            if query.end_date:
                end_dt = parse_datetime_safe(query.end_date)
            eff_limit = query.limit
            eff_offset = query.offset

        records = self.communication_repo.list(filters=effective_filters, limit=1000)

        # Date filtering
        filtered: List[Dict[str, Any]] = []
        for r in records:
            r_dt = parse_datetime_safe(r.get('created_at') or r.get('delivery_timestamp'))
            if start_dt and r_dt and r_dt < start_dt:
                continue
            if end_dt and r_dt and r_dt > end_dt:
                continue
            filtered.append(r)

        filtered.sort(key=lambda x: x.get('id', 0), reverse=True)

        total_count = len(filtered)
        paged = filtered[eff_offset: eff_offset + eff_limit]
        enhanced = [self._enhance_communication_record(r) for r in paged]

        return {
            'total': total_count,
            'limit': eff_limit,
            'offset': eff_offset,
            'items': enhanced,
        }

    # ----------------------------------------------------------------------
    # 5. Delivery Failure Logging & Retry Engine
    # ----------------------------------------------------------------------
    def log_delivery_failure(
        self,
        communication_id: int,
        error_message: str,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an explicit delivery failure event and increment failure count."""
        record = self.communication_repo.get(communication_id)
        if not record:
            raise ValueError(f"Communication record #{communication_id} was not found.")

        meta = record.get('metadata') or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        failure_history = meta.get('failure_history', [])
        failure_event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error_message': error_message,
            'error_code': error_code,
        }
        failure_history.append(failure_event)
        meta['failure_history'] = failure_history
        if metadata:
            meta.update(metadata)

        update_data = {
            'status': 'FAILED',
            'error_message': error_message,
            'metadata': meta,
        }

        updated = self.communication_repo.update(communication_id, update_data)
        return self._enhance_communication_record(updated)

    def retry_communication(
        self,
        communication_id: int,
        max_retries: int = 3,
        force: bool = False,
        custom_recipient: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retry dispatch of a failed communication event.

        Enforces maximum retry threshold, re-evaluates dispatch adapter,
        and logs retry progression history.
        """
        record = self.communication_repo.get(communication_id)
        if not record:
            raise ValueError(f"Communication record #{communication_id} was not found.")

        curr_status = str(record.get('status', '')).upper()
        if curr_status != 'FAILED' and not force:
            return {
                'success': False,
                'communication_id': communication_id,
                'reason': f"Cannot retry communication with status '{curr_status}'. Status must be FAILED (or use force=True).",
            }

        # Check retry limit in metadata
        meta = record.get('metadata') or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        current_retries = int(meta.get('retries', 0))
        if current_retries >= max_retries and not force:
            return {
                'success': False,
                'communication_id': communication_id,
                'reason': f"Max retry limit ({max_retries}) reached for communication #{communication_id}.",
                'retries_attempted': current_retries,
            }

        customer_id = record['customer_id']
        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} does not exist.")

        # Channel & recipient resolution
        channel = str(record.get('channel', 'EMAIL')).upper()
        recipient_addr = custom_recipient or record.get('recipient_address')

        cust_copy = dict(customer)
        if channel == 'EMAIL' and custom_recipient:
            cust_copy['reminder_email'] = custom_recipient
            cust_copy['email'] = custom_recipient
        elif channel == 'WHATSAPP' and custom_recipient:
            cust_copy['reminder_phone'] = custom_recipient
            cust_copy['phone'] = custom_recipient

        # Perform dispatch
        dispatch_success = False
        dispatch_error = None
        new_external_id = None
        now_dt = datetime.now(timezone.utc)

        if channel == 'EMAIL':
            send_res = self.dispatch_service.send_email(
                to_email=recipient_addr,
                subject=record.get('subject') or 'Payment Reminder',
                html_body=record.get('message_body', '').replace('\n', '<br/>'),
                recipient_name=record.get('recipient_name') or customer.get('name'),
                metadata={'communication_id': communication_id, 'is_retry': True},
            )
            dispatch_success = send_res.get('success', False)
            dispatch_error = send_res.get('error_message')
            new_external_id = send_res.get('external_message_id')

        elif channel == 'WHATSAPP':
            send_res = self.dispatch_service.send_whatsapp(
                to_phone=recipient_addr,
                message_text=record.get('message_body', ''),
                metadata={'communication_id': communication_id, 'is_retry': True},
            )
            dispatch_success = send_res.get('success', False)
            dispatch_error = send_res.get('error_message')
            new_external_id = send_res.get('external_message_id')
        else:
            dispatch_error = f"Unsupported channel '{channel}' for retry."

        # Update metadata retry tracking
        new_retry_count = current_retries + 1
        retry_history = meta.get('retry_history', [])
        retry_entry = {
            'retry_number': new_retry_count,
            'timestamp': now_dt.isoformat(),
            'success': dispatch_success,
            'error': dispatch_error,
            'recipient': recipient_addr,
            'external_message_id': new_external_id,
        }
        retry_history.append(retry_entry)
        meta['retries'] = new_retry_count
        meta['last_retry_at'] = now_dt.isoformat()
        meta['retry_history'] = retry_history

        update_fields: Dict[str, Any] = {
            'status': 'SENT' if dispatch_success else 'FAILED',
            'error_message': None if dispatch_success else dispatch_error,
            'metadata': meta,
        }
        if dispatch_success:
            update_fields['delivery_timestamp'] = now_dt
        if new_external_id:
            update_fields['external_message_id'] = new_external_id

        updated = self.communication_repo.update(communication_id, update_fields)

        return {
            'success': dispatch_success,
            'communication_id': communication_id,
            'retry_count': new_retry_count,
            'status': update_fields['status'],
            'error_message': dispatch_error,
            'external_message_id': new_external_id,
            'record': self._enhance_communication_record(updated),
        }

    def get_failed_communications(
        self,
        customer_id: Optional[int] = None,
        limit: int = 50,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """Retrieve failed communications that are eligible for retry."""
        filters: Dict[str, Any] = {'status': 'FAILED'}
        if customer_id:
            filters['customer_id'] = customer_id

        failed_records = self.communication_repo.list(filters=filters, limit=limit * 2)

        eligible: List[Dict[str, Any]] = []
        for rec in failed_records:
            meta = rec.get('metadata') or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            retries = int(meta.get('retries', 0))
            if retries < max_retries:
                eligible.append(self._enhance_communication_record(rec))
                if len(eligible) >= limit:
                    break

        return eligible

    def retry_all_failed(
        self,
        customer_id: Optional[int] = None,
        limit: int = 50,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Batch retry all failed communications that have not exceeded the max retry count."""
        failed_items = self.get_failed_communications(customer_id=customer_id, limit=limit, max_retries=max_retries)

        attempted = 0
        succeeded = 0
        failed = 0
        results = []

        for item in failed_items:
            comm_id = item['id']
            attempted += 1
            res = self.retry_communication(comm_id, max_retries=max_retries)
            results.append(res)
            if res.get('success'):
                succeeded += 1
            else:
                failed += 1

        return {
            'attempted': attempted,
            'succeeded': succeeded,
            'failed': failed,
            'results': results,
        }

    # ----------------------------------------------------------------------
    # 6. Customer Reminder Preferences & VIP Exclusions
    # ----------------------------------------------------------------------
    def get_customer_preferences(self, customer_id: int) -> Dict[str, Any]:
        """Fetch customer reminder preferences, VIP status, and contact routing info."""
        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} does not exist.")

        return {
            'customer_id': customer_id,
            'customer_name': customer.get('name', 'Valued Customer'),
            'is_vip': bool(customer.get('is_vip', False)),
            'exclude_from_reminders': bool(customer.get('exclude_from_reminders', False)),
            'preferred_reminder_channel': customer.get('preferred_reminder_channel', 'EMAIL') or 'EMAIL',
            'reminder_phone': customer.get('reminder_phone') or customer.get('phone'),
            'reminder_email': customer.get('reminder_email') or customer.get('email'),
            'last_reminder_sent_at': customer.get('last_reminder_sent_at'),
            'last_statement_sent_at': customer.get('last_statement_sent_at'),
            'business_id': customer.get('business_id'),
        }

    def update_customer_preferences(
        self,
        customer_id: int,
        preferences: Union[CustomerReminderPreferencesUpdate, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update customer VIP status, reminder exclusion flags, and communication channels."""
        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} does not exist.")

        payload = preferences.model_dump(exclude_unset=True) if isinstance(preferences, CustomerReminderPreferencesUpdate) else dict(preferences)

        allowed_fields = [
            'is_vip',
            'exclude_from_reminders',
            'preferred_reminder_channel',
            'reminder_phone',
            'reminder_email',
        ]

        update_data = {k: v for k, v in payload.items() if k in allowed_fields and v is not None}

        if update_data:
            self.customer_repo.update(customer_id, update_data)

        return self.get_customer_preferences(customer_id)


# Singleton instance helper
customer_communication_service = CustomerCommunicationService()
