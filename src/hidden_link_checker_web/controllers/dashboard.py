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
        history = await _api_client(request).list_link_checks(request.cookies)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == status.HTTP_401_UNAUTHORIZED:
            return HTMLResponse("Authentication required.", status_code=status.HTTP_401_UNAUTHORIZED)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="API unavailable.") from error
    return HTMLResponse(render_dashboard(history))


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
    try:
        link_check = await _api_client(request).get_link_check(check_id, request.cookies)
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    return HTMLResponse(render_link_check(link_check))
