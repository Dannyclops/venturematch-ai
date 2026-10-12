"""Validated demo catalog; file paths are supplied by the host, never the agent."""

import json
from pathlib import Path

from pydantic import Field, model_validator

from app.models import BusinessProfile, FxSnapshot, InvestorProfile, PortfolioCompany
from app.models.common import SchemaModel


class MatchingCatalog(SchemaModel):
    businesses: list[BusinessProfile]
    investors: list[InvestorProfile]
    portfolios: list[PortfolioCompany]
    fx_snapshot: FxSnapshot
    notice: str = Field(min_length=10)

    @model_validator(mode="after")
    def unique_ids(self):
        records = [*self.businesses, *self.investors, *self.portfolios]
        if len({record.id for record in records}) != len(records):
            raise ValueError("Catalog entity IDs must be globally unique.")
        # Missing portfolio references are allowed: the scorer lowers confidence.
        return self

    @classmethod
    def from_demo(cls) -> "MatchingCatalog":
        data = Path(__file__).resolve().parents[3] / "data"
        def read(name):
            return json.loads((data / name).read_text(encoding="utf-8"))
        return cls(
            businesses=read("businesses.json"), investors=read("investors.json"),
            portfolios=read("portfolios.json"), fx_snapshot=read("fx_rates.demo.json"),
            notice="Fictional demo entities and synthetic FX rates; not real investment opportunities.",
        )
