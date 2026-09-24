"""Login, welcome and logout routes backed solely by API authentication endpoints."""

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from hidden_link_checker_web.services.api_client import HiddenLinkCheckerApiClient
from hidden_link_checker_web.views.pages import render_login, render_welcome

router = APIRouter()


def _api_client(request: Request) -> HiddenLinkCheckerApiClient:
    return request.app.state.api_client


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request) -> Response:
    """Show the Google sign-in action, or send an existing session to welcome."""
    client = _api_client(request)
    try:
        await client.get_current_user(request.cookies)
    except httpx.HTTPStatusError as error:
        if error.response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        }:
            return HTMLResponse(render_login(client.google_login_url()))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="API unavailable.") from error
    return RedirectResponse(url="/welcome", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request) -> Response:
    """Show the Google profile name only for the user behind the current session."""
    try:
        user = await _api_client(request).get_current_user(request.cookies)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="API unavailable.") from error
    return HTMLResponse(render_welcome(user))


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Revoke the API session and clear the matching browser cookie."""
    try:
        await _api_client(request).logout(request.cookies)
    except httpx.HTTPStatusError as error:
        if error.response.status_code != status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="API unavailable.") from error
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=request.app.state.session_cookie_name, path="/")
    return response