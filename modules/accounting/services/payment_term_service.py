import logging
from datetime import date, datetime, timedelta
from typing import Optional, Union, Dict, Any, List
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)

PAYMENT_TERM_REPO = CrudRepository(
    'T0096',
    business_columns=[
        'id',
        'name',
        'code',
        'description',
        'due_days',
        'discount_percentage',
        'discount_days',
        'is_active',
        'is_default',
    ],
)

CUSTOMER_REPO = CrudRepository(
    'T0010',
    business_columns=['id', 'name', 'credit_limit', 'balance', 'payment_term_id'],
)

# Standard Common Payment Terms Templates
STANDARD_PAYMENT_TERMS: List[Dict[str, Any]] = [
    {
        'name': 'Net 30',
        'code': 'NET_30',
        'description': 'Payment due within 30 days',
        'due_days': 30,
        'discount_percentage': 0.0,
        'discount_days': 0,
        'is_active': True,
        'is_default': True,
    },
    {
        'name': 'Cash on Delivery (COD)',
        'code': 'COD',
        'description': 'Payment due immediately upon delivery',
        'due_days': 0,
        'discount_percentage': 0.0,
        'discount_days': 0,
        'is_active': True,
        'is_default': False,
    },
    {
        'name': 'Net 15',
        'code': 'NET_15',
        'description': 'Payment due within 15 days',
        'due_days': 15,
        'discount_percentage': 0.0,
        'discount_days': 0,
        'is_active': True,
        'is_default': False,
    },
    {
        'name': 'Net 60',
        'code': 'NET_60',
        'description': 'Payment due within 60 days',
        'due_days': 60,
        'discount_percentage': 0.0,
        'discount_days': 0,
        'is_active': True,
        'is_default': False,
    },
    {
        'name': '2/10 Net 30',
        'code': '2_10_NET_30',
        'description': '2% discount if paid within 10 days, net due in 30 days',
        'due_days': 30,
        'discount_percentage': 2.0,
        'discount_days': 10,
        'is_active': True,
        'is_default': False,
    },
    {
        'name': 'Due on Receipt',
        'code': 'DUE_ON_RECEIPT',
        'description': 'Payment due immediately upon receipt',
        'due_days': 0,
        'discount_percentage': 0.0,
        'discount_days': 0,
        'is_active': True,
        'is_default': False,
    },
]

# Named Standard Term Constants
TERM_NET_30: Dict[str, Any] = STANDARD_PAYMENT_TERMS[0]
TERM_COD: Dict[str, Any] = STANDARD_PAYMENT_TERMS[1]
TERM_NET_15: Dict[str, Any] = STANDARD_PAYMENT_TERMS[2]
TERM_NET_60: Dict[str, Any] = STANDARD_PAYMENT_TERMS[3]
TERM_2_10_NET_30: Dict[str, Any] = STANDARD_PAYMENT_TERMS[4]
TERM_DUE_ON_RECEIPT: Dict[str, Any] = STANDARD_PAYMENT_TERMS[5]

COMMON_PAYMENT_TERMS: Dict[str, Dict[str, Any]] = {
    'NET_30': TERM_NET_30,
    'COD': TERM_COD,
    'NET_15': TERM_NET_15,
    'NET_60': TERM_NET_60,
    '2_10_NET_30': TERM_2_10_NET_30,
    'DUE_ON_RECEIPT': TERM_DUE_ON_RECEIPT,
}

STANDARD_PAYMENT_TERMS_BY_CODE: Dict[str, Dict[str, Any]] = {
    term['code']: term for term in STANDARD_PAYMENT_TERMS
}

# Standard Fallback Term when no terms are configured in database
FALLBACK_NET_30_TERM: Dict[str, Any] = dict(STANDARD_PAYMENT_TERMS[0])


def get_standard_payment_terms() -> List[Dict[str, Any]]:
    """Return a list of standard predefined payment term configurations."""
    return [dict(t) for t in STANDARD_PAYMENT_TERMS]


def get_standard_payment_term(identifier: Union[str, int]) -> Optional[Dict[str, Any]]:
    """
    Look up a standard payment term definition by code, name, or alias.
    Examples: 'COD', 'NET_30', 'Net 30', '2_10_NET_30', '2/10 Net 30', 'NET_15', 'Net 15', 'NET_60', 'Net 60'.
    """
    if not identifier:
        return None
    raw = str(identifier).strip()
    norm = raw.upper().replace(' ', '_').replace('/', '_').replace('-', '_').replace(',', '_').replace('__', '_')

    # Direct match on code
    if raw in STANDARD_PAYMENT_TERMS_BY_CODE:
        return dict(STANDARD_PAYMENT_TERMS_BY_CODE[raw])
    if norm in STANDARD_PAYMENT_TERMS_BY_CODE:
        return dict(STANDARD_PAYMENT_TERMS_BY_CODE[norm])

    # Search through standard terms by name or normalized code
    for term in STANDARD_PAYMENT_TERMS:
        term_norm = term['code'].upper().replace(' ', '_').replace('/', '_').replace('-', '_')
        if norm == term_norm or raw.lower() == term['name'].lower():
            return dict(term)

    # Common aliases
    alias_map = {
        'CASH_ON_DELIVERY': 'COD',
        'CASHONDELIVERY': 'COD',
        '2_10_NET30': '2_10_NET_30',
        '2_10_NET_30': '2_10_NET_30',
        '2_10_NET_30_DAYS': '2_10_NET_30',
        '2_10_N30': '2_10_NET_30',
        'NET15': 'NET_15',
        'NET_15': 'NET_15',
        'NET15DAYS': 'NET_15',
        'NET30': 'NET_30',
        'NET_30': 'NET_30',
        'NET30DAYS': 'NET_30',
        'NET60': 'NET_60',
        'NET_60': 'NET_60',
        'NET60DAYS': 'NET_60',
        'DUE_UPON_RECEIPT': 'DUE_ON_RECEIPT',
        'DUE_RECEIPT': 'DUE_ON_RECEIPT',
    }
    mapped_code = alias_map.get(norm)
    if mapped_code and mapped_code in STANDARD_PAYMENT_TERMS_BY_CODE:
        return dict(STANDARD_PAYMENT_TERMS_BY_CODE[mapped_code])

    return None


def _parse_date(d: Optional[Union[date, datetime, str]]) -> date:
    """
    Normalize date, datetime, or ISO string into a datetime.date object.
    Defaults to date.today() if None or invalid.
    """
    if d is None:
        return date.today()
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        s = d.strip()
        if not s:
            return date.today()
        if 'T' in s or ' ' in s:
            try:
                return datetime.fromisoformat(s).date()
            except Exception:
                pass
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            try:
                return datetime.strptime(s[:10], '%Y-%m-%d').date()
            except Exception as e:
                logger.warning(f"Could not parse date string '{d}': {e}, defaulting to today")
                return date.today()
    return date.today()


def calculate_due_date(
    base_date: Optional[Union[date, datetime, str]] = None,
    term: Optional[Union[dict, Any]] = None,
    due_days: Optional[int] = None,
) -> date:
    """
    Calculate the payment due date from a base date (e.g. delivery date, issue date).

    Args:
        base_date: The starting date for due date calculation (defaults to today).
        term: Payment term dict or object containing `due_days`.
        due_days: Explicit number of days until due (overrides term if provided).

    Returns:
        datetime.date: The calculated due date.
    """
    parsed_date = _parse_date(base_date)

    if due_days is not None:
        days = max(0, int(due_days))
    elif term is not None:
        if isinstance(term, dict):
            days = max(0, int(term.get('due_days', 30) or 0))
        else:
            days = max(0, int(getattr(term, 'due_days', 30) or 0))
    else:
        days = 30

    return parsed_date + timedelta(days=days)


def calculate_discount_deadline(
    base_date: Optional[Union[date, datetime, str]] = None,
    term: Optional[Union[dict, Any]] = None,
    discount_days: Optional[int] = None,
    discount_percentage: Optional[float] = None,
) -> Optional[date]:
    """
    Calculate the early payment discount cutoff date from a base date.

    Args:
        base_date: The starting date (defaults to today).
        term: Payment term dict or object containing `discount_days` and `discount_percentage`.
        discount_days: Explicit number of discount days (overrides term if provided).
        discount_percentage: Explicit discount percentage (overrides term if provided).

    Returns:
        Optional[datetime.date]: The discount cutoff date, or None if no early discount applies.
    """
    parsed_date = _parse_date(base_date)

    if discount_days is not None:
        days = max(0, int(discount_days))
    elif term is not None:
        if isinstance(term, dict):
            days = max(0, int(term.get('discount_days', 0) or 0))
        else:
            days = max(0, int(getattr(term, 'discount_days', 0) or 0))
    else:
        days = 0

    if discount_percentage is not None:
        pct = max(0.0, float(discount_percentage))
    elif term is not None:
        if isinstance(term, dict):
            pct = max(0.0, float(term.get('discount_percentage', 0) or 0))
        else:
            pct = max(0.0, float(getattr(term, 'discount_percentage', 0) or 0))
    else:
        pct = 0.0

    if days > 0 and pct > 0:
        return parsed_date + timedelta(days=days)
    return None


def calculate_max_early_discount(
    total_amount: Union[float, int],
    discount_percentage: Union[float, int],
) -> float:
    """
    Calculate the maximum early discount amount if paid within discount cutoff.

    Args:
        total_amount: Invoice or order total amount.
        discount_percentage: Early payment discount percentage.

    Returns:
        float: Maximum early discount amount rounded to 2 decimal places.
    """
    amt = max(0.0, float(total_amount or 0))
    pct = max(0.0, float(discount_percentage or 0))
    return round(amt * (pct / 100.0), 2)


def calculate_early_discount(
    total_amount: Union[float, int],
    payment_date: Optional[Union[date, datetime, str]] = None,
    discount_due_date: Optional[Union[date, datetime, str]] = None,
    discount_percentage: Optional[float] = None,
    term: Optional[Union[dict, Any]] = None,
    base_date: Optional[Union[date, datetime, str]] = None,
    grace_days: int = 0,
) -> Dict[str, Any]:
    """
    Evaluate whether an early payment discount is valid on a given payment date,
    and calculate discount and net amounts.

    Args:
        total_amount: Total invoice amount.
        payment_date: Date on which payment is being made (defaults to today).
        discount_due_date: Explicit discount cutoff date.
        discount_percentage: Explicit discount percentage.
        term: Payment term dict/object to extract discount parameters.
        base_date: Base date to derive discount deadline if discount_due_date is not passed.
        grace_days: Optional grace period days allowed past discount_due_date.

    Returns:
        Dict[str, Any] with keys:
            - is_eligible: bool
            - discount_percentage: float
            - discount_amount: float
            - net_amount: float
            - discount_due_date: Optional[date]
            - cutoff_date: Optional[date]
            - payment_date: date
            - total_amount: float
            - message: str
    """
    amt = max(0.0, round(float(total_amount or 0), 2))
    pay_date = _parse_date(payment_date)

    if discount_percentage is not None:
        pct = max(0.0, float(discount_percentage))
    elif term is not None:
        if isinstance(term, dict):
            pct = max(0.0, float(term.get('discount_percentage', 0) or 0))
        else:
            pct = max(0.0, float(getattr(term, 'discount_percentage', 0) or 0))
    else:
        pct = 0.0

    if discount_due_date is not None:
        disc_deadline = _parse_date(discount_due_date)
    elif term is not None and base_date is not None:
        disc_deadline = calculate_discount_deadline(base_date, term)
    else:
        disc_deadline = None

    if disc_deadline is not None and pct > 0:
        cutoff = disc_deadline + timedelta(days=max(0, int(grace_days)))
        is_eligible = (pay_date <= cutoff)
    else:
        cutoff = disc_deadline
        is_eligible = False

    if is_eligible:
        raw_discount = amt * (pct / 100.0)
        discount_amount = min(amt, round(raw_discount, 2))
        net_amount = round(amt - discount_amount, 2)
        pct_display = f"{int(pct)}%" if pct.is_integer() else f"{pct:.1f}%"
        message = f"Early payment discount of {pct_display} applied (saved {discount_amount:.2f})"
    else:
        discount_amount = 0.0
        net_amount = amt
        if disc_deadline is not None and pct > 0:
            cutoff_str = cutoff.isoformat() if cutoff else disc_deadline.isoformat()
            message = f"Payment date ({pay_date.isoformat()}) is past the early discount cutoff ({cutoff_str})"
        else:
            message = "No early payment discount applicable"

    return {
        'is_eligible': is_eligible,
        'discount_percentage': pct,
        'discount_amount': discount_amount,
        'net_amount': net_amount,
        'discount_due_date': disc_deadline,
        'cutoff_date': cutoff,
        'payment_date': pay_date,
        'total_amount': amt,
        'message': message,
    }


def resolve_effective_term(
    payment_term_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    customer_repo: Optional[CrudRepository] = None,
    term_repo: Optional[CrudRepository] = None,
    conn=None,
) -> Dict[str, Any]:
    """
    Resolve the applicable payment term using precedence:
    1. Explicit `payment_term_id`
    2. Customer's configured `payment_term_id` (via `customer_id`)
    3. Default active payment term (`is_default = True, is_active = True`)
    4. Any active payment term
    5. Fallback Net 30 default configuration

    Returns:
        Dict[str, Any]: The resolved payment term record/dict.
    """
    t_repo = term_repo or PAYMENT_TERM_REPO
    c_repo = customer_repo or CUSTOMER_REPO
    kwargs = {'conn': conn} if conn is not None else {}

    # 1. Explicit payment_term_id
    if payment_term_id:
        try:
            term = t_repo.get(int(payment_term_id), **kwargs)
            if term:
                return term
        except Exception as e:
            logger.warning(f"Error fetching payment term {payment_term_id}: {e}")

    # 2. Customer payment_term_id
    if customer_id and c_repo:
        try:
            customer = c_repo.get(int(customer_id), **kwargs)
            if customer and customer.get('payment_term_id'):
                term = t_repo.get(int(customer['payment_term_id']), **kwargs)
                if term and term.get('is_active', True):
                    return term
        except Exception as e:
            logger.warning(f"Error fetching customer {customer_id} payment term: {e}")

    # 3. Default active payment term
    try:
        defaults = t_repo.list(filters={'is_default': True, 'is_active': True}, **kwargs)
        if defaults:
            return defaults[0]
    except Exception as e:
        logger.warning(f"Error fetching default payment term: {e}")

    # 4. Any active payment term (prefer NET30 / Net 30)
    try:
        actives = t_repo.list(filters={'is_active': True}, **kwargs)
        if actives:
            for t in actives:
                if t.get('code') in ('NET_30', 'NET30', 'Net 30'):
                    return t
            return actives[0]
    except Exception as e:
        logger.warning(f"Error fetching active payment terms: {e}")

    # 5. Fallback dictionary
    return dict(FALLBACK_NET_30_TERM)


class PaymentTermService(CrudService):
    """
    Domain service for Payment Terms management (T0096) and due date / discount calculation engine.
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or PAYMENT_TERM_REPO)
        self.customer_repo = customer_repo or CUSTOMER_REPO

    def create(self, payload: dict, conn=None) -> dict:
        """
        Create payment term, ensuring only one term is default per tenant if is_default=True.
        """
        if payload.get('is_default'):
            self._unset_existing_defaults(conn=conn)
        return super().create(payload, conn=conn)

    def update(self, id_val: int, payload: dict, conn=None) -> dict:
        """
        Update payment term, resetting other defaults if is_default=True.
        """
        if payload.get('is_default'):
            self._unset_existing_defaults(exclude_id=id_val, conn=conn)
        return super().update(id_val, payload, conn=conn)

    def _unset_existing_defaults(self, exclude_id: Optional[int] = None, conn=None):
        """Unset is_default flag on all existing payment terms for active tenant."""
        try:
            kwargs = {'conn': conn} if conn is not None else {}
            existing_defaults = self.repo.list(filters={'is_default': True}, **kwargs)
            for item in existing_defaults:
                if exclude_id and item.get('id') == exclude_id:
                    continue
                self.repo.update(item['id'], {'is_default': False}, **kwargs)
        except Exception as e:
            logger.warning(f"Could not unset existing default payment terms: {e}")

    def get_default_term(self, conn=None) -> Optional[dict]:
        """Fetch the current default active payment term."""
        kwargs = {'conn': conn} if conn is not None else {}
        defaults = self.repo.list(filters={'is_default': True, 'is_active': True}, **kwargs)
        return defaults[0] if defaults else None

    def get_by_code(self, code: str, conn=None) -> Optional[dict]:
        """Fetch payment term by unique code."""
        kwargs = {'conn': conn} if conn is not None else {}
        terms = self.repo.list(filters={'code': code}, **kwargs)
        return terms[0] if terms else None

    def calculate_due_date(
        self,
        base_date: Optional[Union[date, datetime, str]] = None,
        term: Optional[Union[dict, Any]] = None,
        due_days: Optional[int] = None,
    ) -> date:
        return calculate_due_date(base_date=base_date, term=term, due_days=due_days)

    def calculate_discount_deadline(
        self,
        base_date: Optional[Union[date, datetime, str]] = None,
        term: Optional[Union[dict, Any]] = None,
        discount_days: Optional[int] = None,
        discount_percentage: Optional[float] = None,
    ) -> Optional[date]:
        return calculate_discount_deadline(
            base_date=base_date,
            term=term,
            discount_days=discount_days,
            discount_percentage=discount_percentage,
        )

    def calculate_max_early_discount(
        self,
        total_amount: Union[float, int],
        discount_percentage: Union[float, int],
    ) -> float:
        return calculate_max_early_discount(total_amount, discount_percentage)

    def calculate_early_discount(
        self,
        total_amount: Union[float, int],
        payment_date: Optional[Union[date, datetime, str]] = None,
        discount_due_date: Optional[Union[date, datetime, str]] = None,
        discount_percentage: Optional[float] = None,
        term: Optional[Union[dict, Any]] = None,
        base_date: Optional[Union[date, datetime, str]] = None,
        grace_days: int = 0,
    ) -> Dict[str, Any]:
        return calculate_early_discount(
            total_amount=total_amount,
            payment_date=payment_date,
            discount_due_date=discount_due_date,
            discount_percentage=discount_percentage,
            term=term,
            base_date=base_date,
            grace_days=grace_days,
        )

    def resolve_effective_term(
        self,
        payment_term_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        return resolve_effective_term(
            payment_term_id=payment_term_id,
            customer_id=customer_id,
            customer_repo=self.customer_repo,
            term_repo=self.repo,
            conn=conn,
        )

    def get_standard_terms(self) -> List[Dict[str, Any]]:
        """Return the standard predefined payment term templates."""
        return get_standard_payment_terms()

    def get_standard_term(self, identifier: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Look up a standard payment term definition by code, name, or alias."""
        return get_standard_payment_term(identifier)

    def seed_standard_terms(
        self,
        business_id: Optional[int] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Seed standard payment terms (COD, Net 15, Net 30, Net 60, 2/10 Net 30, Due on Receipt)
        into the database if they don't already exist for the current tenant.
        Ensures active and default term configurations are properly set.

        Returns:
            List of all standard terms (existing or newly created).
        """
        kwargs = {'conn': conn} if conn is not None else {}
        results = []
        try:
            existing_terms = self.repo.list(**kwargs)
            existing_by_code = {
                t.get('code', '').strip().upper(): t for t in existing_terms if t.get('code')
            }
            has_default = any(t.get('is_default') and t.get('is_active', True) for t in existing_terms)

            for std in STANDARD_PAYMENT_TERMS:
                code_key = std['code'].strip().upper()
                if code_key in existing_by_code:
                    results.append(existing_by_code[code_key])
                else:
                    payload = dict(std)
                    if business_id is not None:
                        payload['business_id'] = business_id
                    # If a default already exists, do not duplicate default flag
                    if has_default and payload.get('is_default'):
                        payload['is_default'] = False
                    elif payload.get('is_default'):
                        has_default = True
                    created = self.create(payload, conn=conn)
                    results.append(created)
        except Exception as e:
            logger.error(f"Error seeding standard payment terms: {e}", exc_info=True)
            return get_standard_payment_terms()

        return results


# Module-level default repository and service instances
repo = PAYMENT_TERM_REPO
service = PaymentTermService(PAYMENT_TERM_REPO, CUSTOMER_REPO)
