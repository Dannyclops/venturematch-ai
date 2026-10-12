"""FastAPI entry point for the local, synthetic-data demo."""

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.concurrency import run_in_threadpool

from app.api.contracts import (
    ApiError, ErrorResponse, HealthResponse, MetadataResponse, ProfilePage, ValidationIssue,
)
from app.models import BusinessProfile, InvestorProfile, MatchRequest
from app.models.common import BusinessModel, EntityId, FundingStage, Industry
from app.models.investor import InvestmentRole, InvestorType, StageFlexibility
from app.services.matching import EngineMatchResponse, MatchingServiceError, match_profiles
from app.tools import MatchingCatalog


def create_app(catalog: MatchingCatalog | None = None) -> FastAPI:
    # Load once and fail startup for invalid data, rather than returning empty results.
    source = catalog if catalog is not None else MatchingCatalog.from_demo()
    data = MatchingCatalog.model_validate(source.model_dump()).model_copy(deep=True)
    app = FastAPI(
        title="VentureMatch AI — local matching API", version="0.1.0",
        description="Engine-only matching over fictional demo records and synthetic FX. No AI calls.",
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False, allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    def error_response(status, code, message, issues=None, headers=None):
        body = ErrorResponse(error=ApiError(code=code, message=message, issues=issues or []))
        return JSONResponse(status_code=status, content=body.model_dump(mode="json"), headers=headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, exc):
        # Omit input, validator messages and contexts: they can contain private data.
        # Extra-field names are caller-controlled, so redact their final path element.
        issues = []
        for item in exc.errors()[:20]:
            location = list(item["loc"])
            if item["type"] == "extra_forbidden" and location:
                location[-1] = "<extra_field>"
            issues.append(ValidationIssue(location=location, code=item["type"]))
        return error_response(422, "invalid_request", "Request does not match the schema.", issues)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request, exc):
        messages = {404: ("not_found", "The requested resource was not found."),
                    405: ("method_not_allowed", "This HTTP method is not supported.")}
        code, message = messages.get(exc.status_code, ("http_error", "Request could not be completed."))
        return error_response(exc.status_code, code, message, headers=exc.headers)

    @app.exception_handler(MatchingServiceError)
    async def matching_error(_request, exc):
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(Exception)
    async def unexpected_error(_request, _exc):
        return error_response(500, "internal_error", "The server could not complete the request.")

    @app.get("/api/health", response_model=HealthResponse)
    async def health():
        return HealthResponse()

    @app.get("/api/metadata", response_model=MetadataResponse)
    async def metadata():
        return MetadataResponse(
            industries=list(Industry), funding_stages=list(FundingStage),
            currencies=[rate.currency for rate in data.fx_snapshot.rates],
            business_models=list(BusinessModel), investor_types=list(InvestorType),
            investment_roles=list(InvestmentRole), stage_flexibility=list(StageFlexibility),
            fx_snapshot=data.fx_snapshot, notice=data.notice,
        )

    def page(records, offset, limit):
        ordered = sorted(records, key=lambda profile: profile.id)
        end = offset + limit
        return {"items": ordered[offset:end], "total": len(ordered),
                "next_offset": end if end < len(ordered) else None, "notice": data.notice}

    @app.get("/api/businesses", response_model=ProfilePage[BusinessProfile])
    async def businesses(offset: Annotated[int, Query(ge=0)] = 0,
                         limit: Annotated[int, Query(ge=1, le=50)] = 50):
        return page(data.businesses, offset, limit)

    @app.get("/api/investors", response_model=ProfilePage[InvestorProfile])
    async def investors(offset: Annotated[int, Query(ge=0)] = 0,
                        limit: Annotated[int, Query(ge=1, le=50)] = 50):
        return page(data.investors, offset, limit)

    def find(records, entity_id):
        for profile in records:
            if profile.id == entity_id:
                return profile
        raise HTTPException(status_code=404)

    @app.get("/api/businesses/{entity_id}", response_model=BusinessProfile,
             responses={404: {"model": ErrorResponse}})
    async def business(entity_id: EntityId):
        return find(data.businesses, entity_id)

    @app.get("/api/investors/{entity_id}", response_model=InvestorProfile,
             responses={404: {"model": ErrorResponse}})
    async def investor(entity_id: EntityId):
        return find(data.investors, entity_id)

    @app.post("/api/matches", response_model=EngineMatchResponse,
              responses={503: {"model": ErrorResponse}})
    async def matches(request: MatchRequest):
        # Keep synchronous scoring off the event loop; each request gets its own tools.
        return await run_in_threadpool(match_profiles, request, data)

    return app


app = create_app()
