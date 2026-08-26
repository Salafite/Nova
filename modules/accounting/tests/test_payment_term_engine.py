import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from modules.accounting.services.payment_term_service import (
    PaymentTermService,
    calculate_due_date,
    calculate_discount_deadline,
    calculate_early_discount,
    calculate_max_early_discount,
    resolve_effective_term,
    get_standard_payment_terms,
    get_standard_payment_term,
    _parse_date,
    STANDARD_PAYMENT_TERMS,
    TERM_NET_30,
    TERM_COD,
    TERM_NET_15,
    TERM_NET_60,
    TERM_2_10_NET_30,
    TERM_DUE_ON_RECEIPT,
    FALLBACK_NET_30_TERM,
)
from modules.accounting.controllers import T0096I


class DummyTermObject:
    """Mock-free lightweight object with attributes for duck-typing tests."""
    def __init__(self, due_days=30, discount_days=0, discount_percentage=0.0, is_active=True, is_default=False):
        self.due_days = due_days
        self.discount_days = discount_days
        self.discount_percentage = discount_percentage
        self.is_active = is_active
        self.is_default = is_default


# ==============================================================================
# 1. Date Parsing Helper Tests
# ==============================================================================
class TestParseDate:
    @pytest.mark.parametrize(
        "input_val,expected",
        [
            (None, date.today()),
            (date(2026, 8, 25), date(2026, 8, 25)),
            (datetime(2026, 8, 25, 14, 30, 0), date(2026, 8, 25)),
            ("2026-08-25", date(2026, 8, 25)),
            ("2026-08-25T14:30:00", date(2026, 8, 25)),
            ("2026-08-25T14:30:00Z", date(2026, 8, 25)),
            ("2026-08-25 10:00:00", date(2026, 8, 25)),
            ("", date.today()),
            ("   ", date.today()),
            ("invalid-date-string", date.today()),
        ],
    )
    def test_parse_date_with_various_input_formats_returns_expected_date(self, input_val, expected):
        """Verify _parse_date handles None, date, datetime, ISO strings, and fallback gracefully."""
        assert _parse_date(input_val) == expected


# ==============================================================================
# 2. Due Date Calculation Engine Tests
# ==============================================================================
class TestCalculateDueDate:
    @pytest.mark.parametrize(
        "term_dict,base_str,expected_due_str",
        [
            (TERM_COD, "2026-08-01", "2026-08-01"),
            (TERM_DUE_ON_RECEIPT, "2026-08-01", "2026-08-01"),
            (TERM_NET_15, "2026-08-01", "2026-08-16"),
            (TERM_NET_30, "2026-08-01", "2026-08-31"),
            (TERM_NET_60, "2026-08-01", "2026-09-30"),
            (TERM_2_10_NET_30, "2026-08-01", "2026-08-31"),
        ],
    )
    def test_calculate_due_date_across_standard_terms_computes_exact_offset(
        self, term_dict, base_str, expected_due_str
    ):
        """Ensure standard payment terms (COD, Net 15, Net 30, Net 60, 2/10 Net 30) produce exact due dates."""
        base_d = date.fromisoformat(base_str)
        expected_d = date.fromisoformat(expected_due_str)

        computed = calculate_due_date(base_date=base_d, term=term_dict)
        assert computed == expected_d

    def test_calculate_due_date_with_explicit_due_days_overrides_term(self):
        """Explicit due_days argument must take precedence over term's due_days."""
        base_d = date(2026, 8, 1)
        term = {'due_days': 30}
        computed = calculate_due_date(base_date=base_d, term=term, due_days=45)
        assert computed == date(2026, 9, 15)

    def test_calculate_due_date_with_object_term(self):
        """Duck-typed term objects with attribute due_days are properly resolved."""
        base_d = date(2026, 8, 1)
        term_obj = DummyTermObject(due_days=20)
        computed = calculate_due_date(base_date=base_d, term=term_obj)
        assert computed == date(2026, 8, 21)

    def test_calculate_due_date_with_no_term_defaults_to_30_days(self):
        """When neither term nor due_days is provided, calculation defaults to Net 30 (30 days)."""
        base_d = date(2026, 8, 1)
        computed = calculate_due_date(base_date=base_d, term=None, due_days=None)
        assert computed == date(2026, 8, 31)

    @pytest.mark.parametrize(
        "base_d,days,expected_d",
        [
            # Leap year February (2024 has 29 days)
            (date(2024, 2, 20), 10, date(2024, 3, 1)),
            # Non-leap year February (2025 has 28 days)
            (date(2025, 2, 20), 10, date(2025, 3, 2)),
            # Year boundary transition
            (date(2026, 12, 15), 30, date(2027, 1, 14)),
            # Zero days
            (date(2026, 8, 25), 0, date(2026, 8, 25)),
            # Negative days clamped to 0
            (date(2026, 8, 25), -5, date(2026, 8, 25)),
        ],
    )
    def test_calculate_due_date_boundary_and_leap_year_rollovers(self, base_d, days, expected_d):
        """Due dates across leap years, month ends, and year ends are accurately computed without drifting."""
        computed = calculate_due_date(base_date=base_d, due_days=days)
        assert computed == expected_d

    def test_calculate_due_date_service_wrapper_matches_standalone_function(self):
        """PaymentTermService.calculate_due_date behaves identically to calculate_due_date helper."""
        svc = PaymentTermService()
        base_d = date(2026, 5, 10)
        res_fn = calculate_due_date(base_date=base_d, term=TERM_NET_15)
        res_svc = svc.calculate_due_date(base_date=base_d, term=TERM_NET_15)
        assert res_fn == res_svc == date(2026, 5, 25)


# ==============================================================================
# 3. Discount Deadline Calculation Tests
# ==============================================================================
class TestCalculateDiscountDeadline:
    @pytest.mark.parametrize(
        "term_dict,base_str,expected_cutoff_str",
        [
            (TERM_2_10_NET_30, "2026-08-01", "2026-08-11"),
            ({'discount_days': 15, 'discount_percentage': 3.0}, "2026-08-01", "2026-08-16"),
            (TERM_NET_30, "2026-08-01", None),
            (TERM_COD, "2026-08-01", None),
            (TERM_NET_15, "2026-08-01", None),
            (TERM_NET_60, "2026-08-01", None),
            (TERM_DUE_ON_RECEIPT, "2026-08-01", None),
            ({'discount_days': 10, 'discount_percentage': 0.0}, "2026-08-01", None),
            ({'discount_days': 0, 'discount_percentage': 2.0}, "2026-08-01", None),
        ],
    )
    def test_calculate_discount_deadline_evaluates_correctly_across_terms(
        self, term_dict, base_str, expected_cutoff_str
    ):
        """Discount deadline is only generated when discount_days > 0 and discount_percentage > 0."""
        base_d = date.fromisoformat(base_str)
        expected_d = date.fromisoformat(expected_cutoff_str) if expected_cutoff_str else None

        computed = calculate_discount_deadline(base_date=base_d, term=term_dict)
        assert computed == expected_d

    def test_calculate_discount_deadline_with_explicit_parameters_overrides_term(self):
        """Explicit discount_days and discount_percentage override the term's configured values."""
        base_d = date(2026, 8, 1)
        term = {'discount_days': 0, 'discount_percentage': 0.0}
        computed = calculate_discount_deadline(
            base_date=base_d,
            term=term,
            discount_days=7,
            discount_percentage=1.5,
        )
        assert computed == date(2026, 8, 8)

    def test_calculate_discount_deadline_with_object_term(self):
        """Duck-typed term objects with discount attributes calculate correct deadline."""
        base_d = date(2026, 8, 1)
        term_obj = DummyTermObject(discount_days=5, discount_percentage=2.5)
        computed = calculate_discount_deadline(base_date=base_d, term=term_obj)
        assert computed == date(2026, 8, 6)

    def test_calculate_discount_deadline_service_wrapper_matches_standalone_function(self):
        """PaymentTermService.calculate_discount_deadline behaves identically to calculate_discount_deadline."""
        svc = PaymentTermService()
        base_d = date(2026, 6, 1)
        res_fn = calculate_discount_deadline(base_date=base_d, term=TERM_2_10_NET_30)
        res_svc = svc.calculate_discount_deadline(base_date=base_d, term=TERM_2_10_NET_30)
        assert res_fn == res_svc == date(2026, 6, 11)


# ==============================================================================
# 4. Maximum Early Discount Amount Calculation Tests
# ==============================================================================
class TestCalculateMaxEarlyDiscount:
    @pytest.mark.parametrize(
        "amount,percentage,expected_discount",
        [
            (1000.0, 2.0, 20.0),
            (500.0, 3.0, 15.0),
            (123.45, 2.0, 2.47),  # 123.45 * 0.02 = 2.469 -> 2.47
            (99.99, 1.5, 1.50),   # 99.99 * 0.015 = 1.49985 -> 1.50
            (1000.0, 0.0, 0.0),
            (0.0, 2.0, 0.0),
            (-100.0, 2.0, 0.0),   # Negative amounts clamped to 0
            (100.0, -5.0, 0.0),   # Negative percentage clamped to 0
        ],
    )
    def test_calculate_max_early_discount_computes_rounded_amount(
        self, amount, percentage, expected_discount
    ):
        """Max early discount calculates percentage accurately rounded to 2 decimal places."""
        assert calculate_max_early_discount(amount, percentage) == expected_discount

    def test_calculate_max_early_discount_service_wrapper(self):
        svc = PaymentTermService()
        assert svc.calculate_max_early_discount(1500.0, 2.0) == 30.0


# ==============================================================================
# 5. Early Payment Discount Eligibility & Net Settlement Calculation Tests
# ==============================================================================
class TestCalculateEarlyDiscount:
    def test_calculate_early_discount_paid_before_cutoff_is_eligible(self):
        """Payment made before discount cutoff date receives early discount deduction."""
        result = calculate_early_discount(
            total_amount=1000.0,
            payment_date=date(2026, 8, 5),
            discount_due_date=date(2026, 8, 10),
            discount_percentage=2.0,
        )

        assert result['is_eligible'] is True
        assert result['discount_amount'] == 20.0
        assert result['net_amount'] == 980.0
        assert result['discount_percentage'] == 2.0
        assert result['discount_due_date'] == date(2026, 8, 10)
        assert result['payment_date'] == date(2026, 8, 5)
        assert "Early payment discount of 2% applied" in result['message']

    def test_calculate_early_discount_paid_on_exact_cutoff_date_is_eligible(self):
        """Payment made exactly on the discount deadline date is eligible for discount."""
        result = calculate_early_discount(
            total_amount=500.0,
            payment_date=date(2026, 8, 10),
            discount_due_date=date(2026, 8, 10),
            discount_percentage=3.0,
        )

        assert result['is_eligible'] is True
        assert result['discount_amount'] == 15.0
        assert result['net_amount'] == 485.0

    def test_calculate_early_discount_paid_after_cutoff_is_ineligible(self):
        """Payment made after discount deadline is ineligible; discount amount is 0 and full total is due."""
        result = calculate_early_discount(
            total_amount=1000.0,
            payment_date=date(2026, 8, 11),
            discount_due_date=date(2026, 8, 10),
            discount_percentage=2.0,
        )

        assert result['is_eligible'] is False
        assert result['discount_amount'] == 0.0
        assert result['net_amount'] == 1000.0
        assert "past the early discount cutoff" in result['message']

    def test_calculate_early_discount_with_grace_period_extends_eligibility(self):
        """Grace period allows discount eligibility for specified number of days past discount_due_date."""
        disc_deadline = date(2026, 8, 10)
        grace_days = 2  # Cutoff extended to 2026-08-12

        # Within grace period (August 12)
        within_grace = calculate_early_discount(
            total_amount=1000.0,
            payment_date=date(2026, 8, 12),
            discount_due_date=disc_deadline,
            discount_percentage=2.0,
            grace_days=grace_days,
        )
        assert within_grace['is_eligible'] is True
        assert within_grace['discount_amount'] == 20.0
        assert within_grace['cutoff_date'] == date(2026, 8, 12)

        # Beyond grace period (August 13)
        beyond_grace = calculate_early_discount(
            total_amount=1000.0,
            payment_date=date(2026, 8, 13),
            discount_due_date=disc_deadline,
            discount_percentage=2.0,
            grace_days=grace_days,
        )
        assert beyond_grace['is_eligible'] is False
        assert beyond_grace['discount_amount'] == 0.0
        assert beyond_grace['net_amount'] == 1000.0

    def test_calculate_early_discount_with_base_date_and_term_object(self):
        """Discount deadline is automatically calculated from base_date and term if discount_due_date is omitted."""
        base_d = date(2026, 8, 1)
        term = TERM_2_10_NET_30  # 10 days cutoff -> 2026-08-11

        result = calculate_early_discount(
            total_amount=2000.0,
            payment_date=date(2026, 8, 9),
            base_date=base_d,
            term=term,
        )

        assert result['is_eligible'] is True
        assert result['discount_due_date'] == date(2026, 8, 11)
        assert result['discount_amount'] == 40.0
        assert result['net_amount'] == 1960.0

    def test_calculate_early_discount_with_non_discount_term(self):
        """Standard terms without discounts (e.g. Net 30, COD) always result in ineligible status and 0 discount."""
        result = calculate_early_discount(
            total_amount=1000.0,
            payment_date=date(2026, 8, 5),
            term=TERM_NET_30,
            base_date=date(2026, 8, 1),
        )

        assert result['is_eligible'] is False
        assert result['discount_amount'] == 0.0
        assert result['net_amount'] == 1000.0
        assert result['message'] == "No early payment discount applicable"

    def test_calculate_early_discount_service_wrapper(self):
        """PaymentTermService.calculate_early_discount returns identical evaluation."""
        svc = PaymentTermService()
        res = svc.calculate_early_discount(
            total_amount=500.0,
            payment_date=date(2026, 8, 5),
            discount_due_date=date(2026, 8, 10),
            discount_percentage=2.0,
        )
        assert res['is_eligible'] is True
        assert res['discount_amount'] == 10.0
        assert res['net_amount'] == 490.0


# ==============================================================================
# 6. Standard Predefined Payment Terms Registry & Lookup Tests
# ==============================================================================
class TestStandardPaymentTermsLookup:
    def test_get_standard_payment_terms_returns_all_predefined_configurations(self):
        """Ensure standard templates contain all required standard terms."""
        terms = get_standard_payment_terms()
        codes = [t['code'] for t in terms]

        assert 'NET_30' in codes
        assert 'COD' in codes
        assert 'NET_15' in codes
        assert 'NET_60' in codes
        assert '2_10_NET_30' in codes
        assert 'DUE_ON_RECEIPT' in codes
        assert len(terms) >= 6

    @pytest.mark.parametrize(
        "query,expected_code",
        [
            ("COD", "COD"),
            ("Cash on Delivery (COD)", "COD"),
            ("cash on delivery", "COD"),
            ("cashondelivery", "COD"),
            ("NET_30", "NET_30"),
            ("Net 30", "NET_30"),
            ("net30", "NET_30"),
            ("net 30 days", "NET_30"),
            ("NET30DAYS", "NET_30"),
            ("NET_15", "NET_15"),
            ("Net 15", "NET_15"),
            ("net15", "NET_15"),
            ("NET_60", "NET_60"),
            ("Net 60", "NET_60"),
            ("net60", "NET_60"),
            ("2_10_NET_30", "2_10_NET_30"),
            ("2/10 Net 30", "2_10_NET_30"),
            ("2_10_net30", "2_10_NET_30"),
            ("2_10_net_30_days", "2_10_NET_30"),
            ("2_10_n30", "2_10_NET_30"),
            ("Due on Receipt", "DUE_ON_RECEIPT"),
            ("DUE_ON_RECEIPT", "DUE_ON_RECEIPT"),
            ("due_upon_receipt", "DUE_ON_RECEIPT"),
        ],
    )
    def test_get_standard_payment_term_resolves_exact_and_alias_queries(self, query, expected_code):
        """Lookup resolves codes, human-readable names, and common aliases to correct template."""
        matched = get_standard_payment_term(query)
        assert matched is not None
        assert matched['code'] == expected_code

    def test_get_standard_payment_term_unknown_identifier_returns_none(self):
        """Unrecognized codes or empty queries return None."""
        assert get_standard_payment_term(None) is None
        assert get_standard_payment_term("") is None
        assert get_standard_payment_term("UNKNOWN_TERM_XYZ") is None


# ==============================================================================
# 7. Payment Term Precedence & Resolution Tests
# ==============================================================================
class TestResolveEffectiveTerm:
    def setup_method(self):
        self.mock_term_repo = MagicMock()
        self.mock_customer_repo = MagicMock()

    def test_resolve_effective_term_explicit_payment_term_id_takes_highest_precedence(self):
        """Explicit payment_term_id takes precedence over customer settings and database defaults."""
        self.mock_term_repo.get.return_value = {
            'id': 5,
            'code': 'NET_15',
            'due_days': 15,
            'discount_percentage': 0.0,
            'discount_days': 0,
        }

        resolved = resolve_effective_term(
            payment_term_id=5,
            customer_id=100,
            customer_repo=self.mock_customer_repo,
            term_repo=self.mock_term_repo,
        )

        assert resolved['id'] == 5
        assert resolved['code'] == 'NET_15'
        self.mock_term_repo.get.assert_called_once_with(5)
        # Customer repo should not even be queried
        self.mock_customer_repo.get.assert_not_called()

    def test_resolve_effective_term_customer_term_id_takes_second_precedence(self):
        """When payment_term_id is not passed, customer's configured payment_term_id is resolved."""
        self.mock_customer_repo.get.return_value = {
            'id': 100,
            'name': 'Gourmet Bistro',
            'payment_term_id': 8,
        }
        self.mock_term_repo.get.return_value = {
            'id': 8,
            'code': '2_10_NET_30',
            'due_days': 30,
            'discount_percentage': 2.0,
            'discount_days': 10,
            'is_active': True,
        }

        resolved = resolve_effective_term(
            payment_term_id=None,
            customer_id=100,
            customer_repo=self.mock_customer_repo,
            term_repo=self.mock_term_repo,
        )

        assert resolved['id'] == 8
        assert resolved['code'] == '2_10_NET_30'
        assert resolved['discount_percentage'] == 2.0
        self.mock_customer_repo.get.assert_called_once_with(100)
        self.mock_term_repo.get.assert_called_once_with(8)

    def test_resolve_effective_term_customer_inactive_term_falls_through_to_default(self):
        """If customer's configured term is inactive (is_active=False), fallback to tenant default term."""
        self.mock_customer_repo.get.return_value = {
            'id': 100,
            'payment_term_id': 9,
        }
        # Customer's term is inactive
        self.mock_term_repo.get.return_value = {
            'id': 9,
            'code': 'OLD_TERM',
            'is_active': False,
        }
        # Tenant default term
        self.mock_term_repo.list.return_value = [
            {
                'id': 1,
                'code': 'NET_30',
                'due_days': 30,
                'is_default': True,
                'is_active': True,
            }
        ]

        resolved = resolve_effective_term(
            payment_term_id=None,
            customer_id=100,
            customer_repo=self.mock_customer_repo,
            term_repo=self.mock_term_repo,
        )

        assert resolved['id'] == 1
        assert resolved['code'] == 'NET_30'

    def test_resolve_effective_term_default_active_term_takes_third_precedence(self):
        """When neither explicit nor customer term exists, active default term from DB is returned."""
        self.mock_term_repo.list.return_value = [
            {
                'id': 2,
                'code': 'NET_30',
                'due_days': 30,
                'is_default': True,
                'is_active': True,
            }
        ]

        resolved = resolve_effective_term(
            payment_term_id=None,
            customer_id=None,
            customer_repo=self.mock_customer_repo,
            term_repo=self.mock_term_repo,
        )

        assert resolved['id'] == 2
        assert resolved['code'] == 'NET_30'
        self.mock_term_repo.list.assert_called_once_with(filters={'is_default': True, 'is_active': True})

    def test_resolve_effective_term_any_active_term_takes_fourth_precedence(self):
        """When no default exists, any active term in DB is returned (preferring NET_30)."""
        # First call (default) returns empty, second call (active) returns list
        self.mock_term_repo.list.side_effect = [
            [],  # No defaults
            [
                {'id': 3, 'code': 'COD', 'due_days': 0, 'is_active': True},
                {'id': 4, 'code': 'NET_30', 'due_days': 30, 'is_active': True},
            ],
        ]

        resolved = resolve_effective_term(
            payment_term_id=None,
            customer_id=None,
            customer_repo=self.mock_customer_repo,
            term_repo=self.mock_term_repo,
        )

        # Prefers NET_30 among active terms
        assert resolved['code'] == 'NET_30'
        assert resolved['id'] == 4

    def test_resolve_effective_term_empty_database_returns_fallback_net_30(self):
        """When database has no terms at all, returns fallback Net 30 default dictionary."""
        self.mock_term_repo.list.side_effect = [[], []]

        resolved = resolve_effective_term(
            payment_term_id=None,
            customer_id=None,
            customer_repo=self.mock_customer_repo,
            term_repo=self.mock_term_repo,
        )

        assert resolved['code'] == FALLBACK_NET_30_TERM['code']
        assert resolved['due_days'] == 30
        assert resolved['discount_percentage'] == 0.0


# ==============================================================================
# 8. PaymentTermService Management & Seeding Tests
# ==============================================================================
class TestPaymentTermServiceManagement:
    def setup_method(self):
        self.mock_term_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.service = PaymentTermService(self.mock_term_repo, self.mock_customer_repo)

    def test_create_payment_term_with_is_default_unsets_previous_defaults(self):
        """Creating a new default term automatically unsets is_default on existing terms."""
        self.mock_term_repo.list.return_value = [
            {'id': 1, 'code': 'NET_30', 'is_default': True},
        ]
        self.mock_term_repo.create.return_value = {
            'id': 10,
            'code': 'NET_15',
            'is_default': True,
        }

        payload = {'code': 'NET_15', 'name': 'Net 15', 'due_days': 15, 'is_default': True}
        result = self.service.create(payload)

        # Verify old default was unset
        self.mock_term_repo.update.assert_called_once_with(1, {'is_default': False})
        # Verify new term was created
        self.mock_term_repo.create.assert_called_once_with(payload)
        assert result['id'] == 10

    def test_update_payment_term_with_is_default_unsets_other_defaults(self):
        """Updating a term to is_default=True unsets other terms but excludes itself."""
        self.mock_term_repo.list.return_value = [
            {'id': 1, 'code': 'NET_30', 'is_default': True},
            {'id': 2, 'code': '2_10_NET_30', 'is_default': True},
        ]
        self.mock_term_repo.update.return_value = {
            'id': 2,
            'code': '2_10_NET_30',
            'is_default': True,
        }

        result = self.service.update(2, {'is_default': True})

        # ID 1 was unset, but ID 2 was excluded from unsetting
        self.mock_term_repo.update.assert_any_call(1, {'is_default': False})
        assert result['id'] == 2

    def test_get_default_term_returns_active_default_record(self):
        """get_default_term queries repo for is_default=True and is_active=True."""
        self.mock_term_repo.list.return_value = [
            {'id': 1, 'code': 'NET_30', 'is_default': True, 'is_active': True}
        ]

        term = self.service.get_default_term()
        assert term is not None
        assert term['code'] == 'NET_30'
        self.mock_term_repo.list.assert_called_once_with(filters={'is_default': True, 'is_active': True})

    def test_get_by_code_queries_repo_by_code(self):
        """get_by_code queries repo with code filter."""
        self.mock_term_repo.list.return_value = [
            {'id': 3, 'code': 'COD', 'name': 'Cash on Delivery'}
        ]

        term = self.service.get_by_code('COD')
        assert term is not None
        assert term['code'] == 'COD'
        self.mock_term_repo.list.assert_called_once_with(filters={'code': 'COD'})

    def test_seed_standard_terms_creates_missing_terms(self):
        """seed_standard_terms seeds standard terms into database if they do not exist."""
        # Assume empty database
        self.mock_term_repo.list.return_value = []
        self.mock_term_repo.create.side_effect = lambda data, conn=None: {'id': 99, **data}

        results = self.service.seed_standard_terms(business_id=1)

        assert len(results) == len(STANDARD_PAYMENT_TERMS)
        # All created with business_id = 1
        assert all(r.get('business_id') == 1 for r in results)

    def test_seed_standard_terms_skips_existing_terms(self):
        """seed_standard_terms does not duplicate terms that already exist by code."""
        self.mock_term_repo.list.return_value = [
            {'id': 1, 'code': 'NET_30', 'name': 'Net 30', 'is_default': True, 'is_active': True}
        ]
        self.mock_term_repo.create.side_effect = lambda data, conn=None: {'id': 100, **data}

        results = self.service.seed_standard_terms()

        # NET_30 was existing, remaining 5 were created
        assert len(results) == len(STANDARD_PAYMENT_TERMS)
        assert self.mock_term_repo.create.call_count == len(STANDARD_PAYMENT_TERMS) - 1


# ==============================================================================
# 9. Payment Terms Controller (T0096I) Route Tests
# ==============================================================================
class TestPaymentTermControllerRoutes:
    def test_get_default_payment_term_endpoint(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.get_default_term.return_value = {
            'id': 1,
            'name': 'Net 30',
            'code': 'NET_30',
            'due_days': 30,
            'discount_percentage': 0.0,
            'discount_days': 0,
            'is_active': True,
            'is_default': True,
        }
        monkeypatch.setattr(T0096I, 'service', mock_svc)

        result = T0096I.get_default_payment_term()
        assert result['code'] == 'NET_30'
        assert result['is_default'] is True

    def test_get_default_payment_term_404_when_none_exists(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.get_default_term.return_value = None
        monkeypatch.setattr(T0096I, 'service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0096I.get_default_payment_term()
        assert exc_info.value.status_code == 404

    def test_get_standard_payment_terms_endpoint(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.get_standard_terms.return_value = STANDARD_PAYMENT_TERMS
        monkeypatch.setattr(T0096I, 'service', mock_svc)

        result = T0096I.get_standard_payment_terms()
        assert len(result) == len(STANDARD_PAYMENT_TERMS)
        assert result[0]['code'] == 'NET_30'

    def test_seed_standard_payment_terms_endpoint(self, monkeypatch):
        mock_svc = MagicMock()
        mock_svc.seed_standard_terms.return_value = [
            {
                'id': 1,
                'name': 'Net 30',
                'code': 'NET_30',
                'due_days': 30,
                'discount_percentage': 0.0,
                'discount_days': 0,
                'is_active': True,
                'is_default': True,
            }
        ]
        monkeypatch.setattr(T0096I, 'service', mock_svc)

        result = T0096I.seed_standard_payment_terms()
        assert len(result) == 1
        assert result[0]['code'] == 'NET_30'
