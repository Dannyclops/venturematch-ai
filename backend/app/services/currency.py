"""Transparent, snapshot-based currency normalization for matching."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from app.models.common import (
    FxSnapshot,
    MoneyAmount,
    MoneyRange,
    NormalizedMoneyAmount,
    NormalizedMoneyRange,
    SupportedCurrency,
)


TWO_DECIMAL_PLACES = Decimal("0.01")


class UnsupportedCurrencyError(ValueError):
    """Raised when the selected FX snapshot has no rate for a currency."""


class CurrencyNormalizer:
    """Converts original user-entered money into one comparison currency."""

    def __init__(self, snapshot: FxSnapshot) -> None:
        self.snapshot = snapshot
        self._rates = {rate.currency: rate.rate_to_base for rate in snapshot.rates}

    @classmethod
    def from_json_file(cls, path: str | Path) -> "CurrencyNormalizer":
        snapshot = FxSnapshot.model_validate_json(Path(path).read_text(encoding="utf-8"))
        return cls(snapshot)

    def rate_for(self, currency: SupportedCurrency) -> Decimal:
        try:
            return self._rates[currency]
        except KeyError as error:
            raise UnsupportedCurrencyError(
                f"No {currency.value} conversion rate is available in this snapshot"
            ) from error

    def normalize_amount(self, value: MoneyAmount) -> NormalizedMoneyAmount:
        rate = self.rate_for(value.currency)
        normalized = (Decimal(value.amount) * rate).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )
        return NormalizedMoneyAmount(
            original=value,
            normalized_amount=normalized,
            normalized_currency=self.snapshot.base_currency,
            exchange_rate=rate,
            rate_timestamp=self.snapshot.as_of,
            rate_source=self.snapshot.source,
            is_estimate=True,
        )

    def normalize_range(self, value: MoneyRange) -> NormalizedMoneyRange:
        rate = self.rate_for(value.currency)
        normalized_minimum = (Decimal(value.minimum) * rate).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )
        normalized_maximum = (Decimal(value.maximum) * rate).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )
        return NormalizedMoneyRange(
            original=value,
            normalized_minimum=normalized_minimum,
            normalized_maximum=normalized_maximum,
            normalized_currency=self.snapshot.base_currency,
            exchange_rate=rate,
            rate_timestamp=self.snapshot.as_of,
            rate_source=self.snapshot.source,
            is_estimate=True,
        )

