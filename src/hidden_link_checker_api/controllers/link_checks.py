"""HTTP endpoints for link check creation, history, detail and deletion."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from hidden_link_checker_api.domain.models import AuthenticatedUser, LinkCheck
from hidden_link_checker_api.scanner.urls import InvalidInputUrlError
from hidden_link_checker_api.services.auth import AuthenticationService
from hidden_link_checker_api.services.link_checks import LinkCheckService
from shared_contracts.api_models import (
    CreateLinkCheckRequest,
    CreateLinkCheckResponse,
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
    """Return the service assembled by the API application factory."""
    return request.app.state.link_check_service


def _to_response(link_check: LinkCheck) -> LinkCheckResponse:
    return LinkCheckResponse(
        check_id=link_check.id,
        status=link_check.status.value,
        submitted_url=link_check.submitted_url,
        normalized_url=link_check.normalized_url,
        final_url=link_check.final_url,
        dom_reference=link_check.dom_reference if link_check.include_dom else None,
        limitations=link_check.limitations,
        created_at=link_check.created_at,
        completed_at=link_check.completed_at,
        links=[
            LinkResultResponse(
                id=result.id,
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


@router.post("/link-checks", response_model=CreateLinkCheckResponse, status_code=status.HTTP_202_ACCEPTED)
def create_link_check(
    payload: CreateLinkCheckRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: LinkCheckService = Depends(get_link_check_service),
) -> CreateLinkCheckResponse:
    """Queue a link check for the authenticated user."""
    try:
        link_check = service.create(user, payload.url, payload.include_dom)
    except InvalidInputUrlError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return CreateLinkCheckResponse(
        check_id=link_check.id,
        status=link_check.status.value,
        created_at=link_check.created_at,
    )


@router.get("/me/link-checks", response_model=list[LinkCheckHistoryItem])
def list_link_checks(
    user: AuthenticatedUser = Depends(get_current_user),
    service: LinkCheckService = Depends(get_link_check_service),
) -> list[LinkCheckHistoryItem]:
    """List link checks owned by the authenticated user."""
    return [
        LinkCheckHistoryItem(
            check_id=link_check.id,
            status=link_check.status.value,
            submitted_url=link_check.submitted_url,
            created_at=link_check.created_at,
            completed_at=link_check.completed_at,
        )
        for link_check in service.list(user)
    ]


@router.get("/link-checks/{check_id}", response_model=LinkCheckResponse)
def get_link_check(
    check_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: LinkCheckService = Depends(get_link_check_service),
) -> LinkCheckResponse:
    """Return one owned link check without revealing cross-account records."""
    link_check = service.get(user, check_id)
    if link_check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link check not found.")
    return _to_response(link_check)


@router.delete("/link-checks/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link_check(
    check_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: LinkCheckService = Depends(get_link_check_service),
) -> Response:
    """Delete one owned link check and its dependent records."""
    if not service.delete(user, check_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link check not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
