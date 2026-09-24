"""Dashboard and detail routes backed only by the API module."""

from uuid import UUID

import httpx
from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from hidden_link_checker_web.services.api_client import HiddenLinkCheckerApiClient
from hidden_link_checker_web.views.pages import render_dashboard, render_link_check

router = APIRouter()


def _api_client(request: Request) -> HiddenLinkCheckerApiClient:
    return request.app.state.api_client


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Show the URL form and authenticated user's link-check history."""
    try:
        client = _api_client(request)
        user = await client.get_current_user(request.cookies)
        history = await client.list_link_checks(request.cookies)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="API unavailable.") from error
    return HTMLResponse(render_dashboard(history, user))


@router.get("/link-checks", response_class=HTMLResponse)
async def link_checks_page(request: Request) -> HTMLResponse:
    """Expose the dashboard at the link-checks collection URL as well."""
    return await dashboard(request)


@router.post("/link-checks")
async def create_link_check(
    request: Request,
    url: str = Form(),
    include_dom: bool = Form(default=False),
) -> RedirectResponse:
    """Submit a URL to the API and redirect to its detail page."""
    try:
        created_check = await _api_client(request).create_link_check(url, include_dom, request.cookies)
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    return RedirectResponse(url=f"/link-checks/{created_check.check_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/link-checks/{check_id}", response_class=HTMLResponse)
async def link_check_detail(check_id: UUID, request: Request) -> HTMLResponse:
    """Show the result data returned by the API."""
    page = int(request.query_params.get("page", "1"))
    page_size = int(request.query_params.get("page_size", "20"))
    page = max(page, 1)
    page_size = min(max(page_size, 20), 100)
    try:
        link_check = await _api_client(request).get_link_check(
            check_id, request.cookies, page=page, page_size=page_size
        )
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    return HTMLResponse(render_link_check(link_check))
