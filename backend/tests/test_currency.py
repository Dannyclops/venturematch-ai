"""Tests for reproducible currency normalization."""

from datetime import datetime, timezone
from decimal import Decimal

from app.models import FxRate, FxSnapshot, MoneyAmount, MoneyRange, SupportedCurrency
from app.services import CurrencyNormalizer


def normalizer() -> CurrencyNormalizer:
    snapshot = FxSnapshot(
        base_currency=SupportedCurrency.USD,
        as_of=datetime(2026, 10, 12, tzinfo=timezone.utc),
        source="synthetic_test_snapshot",
        is_live=False,
        rates=[
            FxRate(currency=SupportedCurrency.USD, rate_to_base=Decimal("1")),
            FxRate(currency=SupportedCurrency.NGN, rate_to_base=Decimal("0.000625")),
            FxRate(currency=SupportedCurrency.EUR, rate_to_base=Decimal("1.10")),
        ],
        notice="Synthetic rates used exclusively for automated tests.",
    )
    return CurrencyNormalizer(snapshot)


def test_normalizes_local_currency_and_preserves_original() -> None:
    result = normalizer().normalize_amount(
        MoneyAmount(amount=1_200_000_000, currency=SupportedCurrency.NGN)
    )

    assert result.original.amount == 1_200_000_000
    assert result.original.currency is SupportedCurrency.NGN
    assert result.normalized_amount == Decimal("750000.00")
    assert result.normalized_currency is SupportedCurrency.USD
    assert result.exchange_rate == Decimal("0.000625")
    assert result.rate_source == "synthetic_test_snapshot"


def test_normalizes_both_ends_of_investor_ticket_range() -> None:
    result = normalizer().normalize_range(
        MoneyRange(minimum=140_000, maximum=920_000, currency=SupportedCurrency.EUR)
    )

    assert result.normalized_minimum == Decimal("154000.00")
    assert result.normalized_maximum == Decimal("1012000.00")

