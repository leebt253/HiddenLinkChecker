"""Google OIDC, current-user and logout endpoints."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from hidden_link_checker_api.config import ApiSettings
from hidden_link_checker_api.services.auth import AuthenticationService, InvalidOAuthCallbackError
from shared_contracts.api_models import CurrentUserResponse

router = APIRouter(prefix="/v1", tags=["authentication"])


def _authentication_service(request: Request) -> AuthenticationService:
    service = request.app.state.authentication_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured.",
        )
    return service


def _settings(request: Request) -> ApiSettings:
    return request.app.state.settings


@router.get("/auth/google/start")
def start_google_login(request: Request) -> RedirectResponse:
    """Create a one-time OIDC transaction and redirect the browser to Google."""
    return RedirectResponse(url=_authentication_service(request).begin_google_login())


@router.get("/auth/google/callback")
async def complete_google_login(code: str, state: str, request: Request) -> RedirectResponse:
    """Verify Google identity, establish an opaque session and open the dashboard."""
    try:
        _, session_token = await _authentication_service(request).complete_google_login(code, state)
    except InvalidOAuthCallbackError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    settings = _settings(request)
    response = RedirectResponse(url=f"{settings.web_base_url.rstrip('/')}/", status_code=303)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_lifetime_days * 24 * 60 * 60,
        path="/",
    )
    return response


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    """Revoke the current server-side session and clear its browser cookie."""
    settings = _settings(request)
    _authentication_service(request).logout(request.cookies.get(settings.session_cookie_name))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return response


@router.get("/me", response_model=CurrentUserResponse)
def current_user(request: Request) -> CurrentUserResponse:
    """Return the profile belonging to the session cookie, never to a caller-supplied user ID."""
    settings = _settings(request)
    user = _authentication_service(request).get_user_from_session(
        request.cookies.get(settings.session_cookie_name)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return CurrentUserResponse(
        id=user.id, email=user.email, display_name=user.display_name, avatar_url=user.avatar_url
    )