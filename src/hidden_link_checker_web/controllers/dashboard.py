"""Dashboard and detail routes backed only by the API module."""

from uuid import UUID

import httpx
from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from hidden_link_checker_web.services.api_client import HiddenLinkCheckerApiClient
from hidden_link_checker_web.views.pages import render_dashboard, render_error, render_link_check

router = APIRouter()


def _api_client(request: Request) -> HiddenLinkCheckerApiClient:
    return request.app.state.api_client


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, recent_page: int = Query(default=1, ge=1)) -> HTMLResponse:
    """Show the URL form and authenticated user's link-check history."""
    try:
        client = _api_client(request)
        user = await client.get_current_user(request.cookies)
        history = await client.list_link_checks(request.cookies)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="API unavailable.") from error
    return HTMLResponse(render_dashboard(history, user, recent_page=recent_page))


@router.get("/link-checks", response_class=HTMLResponse)
async def link_checks_page(request: Request, recent_page: int = Query(default=1, ge=1)) -> HTMLResponse:
    """Expose the dashboard at the link-checks collection URL as well."""
    return await dashboard(request, recent_page=recent_page)


@router.post("/link-checks")
async def create_link_check(
    request: Request,
    url: str = Form(),
) -> HTMLResponse:
    """Run the check and display its response without storing scan details."""
    try:
        result = await _api_client(request).create_link_check(url, request.cookies)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        return HTMLResponse(
            render_error(error.response.status_code, "Could not check this URL", "Review the URL and try again."),
            status_code=error.response.status_code,
        )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="API unavailable.") from error
    return HTMLResponse(render_link_check(result))


@router.post("/link-checks/{check_id}/delete")
async def delete_link_check_history(check_id: UUID, request: Request) -> RedirectResponse:
    """Delete a history item through the API and return to the dashboard."""
    try:
        await _api_client(request).delete_link_check(check_id, request.cookies)
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail="Could not delete URL history.") from error
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
