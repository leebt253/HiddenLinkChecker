"""Synchronous URL check and ownership-scoped history endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from hidden_link_checker_api.domain.models import AuthenticatedUser, LinkCheck
from hidden_link_checker_api.services.auth import AuthenticationService
from hidden_link_checker_api.services.link_checks import LinkCheckService
from shared_contracts.api_models import (
    CreateLinkCheckRequest,
    LinkCheckHistoryItem,
    LinkCheckResponse,
    LinkResultResponse,
)

router = APIRouter(prefix="/v1", tags=["link-checks"])


def get_current_user(request: Request) -> AuthenticatedUser:
    """Resolve the authenticated user from the opaque server-side session cookie."""
    settings = request.app.state.settings
    service: AuthenticationService | None = request.app.state.authentication_service
    if service is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    user = service.get_user_from_session(request.cookies.get(settings.session_cookie_name))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return AuthenticatedUser(id=user.id)


def get_link_check_service(request: Request) -> LinkCheckService:
    return request.app.state.link_check_service


def _to_response(link_check: LinkCheck) -> LinkCheckResponse:
    return LinkCheckResponse(
        check_id=link_check.id,
        status=link_check.status.value,
        submitted_url=link_check.submitted_url,
        normalized_url=link_check.normalized_url or None,
        final_url=link_check.final_url,
        http_status=link_check.http_status,
        error_code=link_check.error_code,
        dom_excerpt=link_check.dom_excerpt,
        limitations=link_check.limitations,
        checked_at=link_check.created_at,
        links=[
            LinkResultResponse(
                element_type=result.element_type.value,
                object_reference=result.object_reference,
                source_url=result.source_url,
                actual_url=result.actual_url,
                visibility=result.visibility.value,
                visible_text=result.visible_text,
                alt_text=result.alt_text,
                position=result.position,
            )
            for result in link_check.links
        ],
    )


@router.post("/link-checks", response_model=LinkCheckResponse)
def create_link_check(
    payload: CreateLinkCheckRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: LinkCheckService = Depends(get_link_check_service),
) -> LinkCheckResponse:
    """Inspect one submitted URL and return all findings in this response."""
    return _to_response(service.check(user, payload.url))


@router.get("/me/link-checks", response_model=list[LinkCheckHistoryItem])
def list_link_checks(
    user: AuthenticatedUser = Depends(get_current_user),
    service: LinkCheckService = Depends(get_link_check_service),
) -> list[LinkCheckHistoryItem]:
    """List only the user's URL and check timestamp history."""
    return [
        LinkCheckHistoryItem(check_id=item.id, url=item.url, checked_at=item.checked_at)
        for item in service.list_history(user)
    ]


@router.delete("/me/link-checks/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link_check_history(
    check_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: LinkCheckService = Depends(get_link_check_service),
) -> Response:
    """Delete one history item without exposing records belonging to other users."""
    if not service.delete_history(user, check_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL history item not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
