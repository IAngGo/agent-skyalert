"""
FastAPI router for user management endpoints.

POST /users    — register a new user
GET  /users/{user_id} — retrieve a user by ID
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.application.commands import CreateUserCommand
from backend.application.use_cases.create_search import CreateSearch
from backend.domain.entities import User
from backend.infrastructure.api.deps import get_current_user
from backend.infrastructure.api.schemas import CreateUserRequest, UserResponse
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.user_repository import PostgresUserRepository

router = APIRouter(prefix="/users", tags=["users"])


def _get_user_repo(db: Session = Depends(get_db)) -> PostgresUserRepository:
    """
    FastAPI dependency that provides a scoped UserRepository.

    Args:
        db: SQLAlchemy session from get_db().

    Returns:
        A PostgresUserRepository bound to the current session.
    """
    return PostgresUserRepository(db)


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    body: CreateUserRequest,
    repo: PostgresUserRepository = Depends(_get_user_repo),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Register a new SkyAlert user.

    Args:
        body: Validated request body with email, phone, and whatsapp_enabled.
        repo: Injected UserRepository.
        db: SQLAlchemy session for committing.

    Returns:
        The created User as a UserResponse.
    """
    user = User(
        id=uuid4(),
        email=body.email,
        phone=body.phone,
        whatsapp_enabled=body.whatsapp_enabled,
        created_at=datetime.now(timezone.utc),
    )
    saved = repo.save(user)
    db.commit()
    return UserResponse(
        id=saved.id,
        email=saved.email,
        phone=saved.phone,
        whatsapp_enabled=saved.whatsapp_enabled,
        created_at=saved.created_at,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    repo: PostgresUserRepository = Depends(_get_user_repo),
    current_user_id: UUID = Depends(get_current_user),
) -> UserResponse:
    """
    Retrieve a user by UUID. Users can only retrieve their own profile.

    Args:
        user_id: String UUID path parameter.
        repo: Injected UserRepository.
        current_user_id: UUID from the authenticated JWT.

    Returns:
        The User as a UserResponse.

    Raises:
        UserNotFoundError: If no user exists with the given ID (→ 404).
        HTTPException 403: If user_id does not match the authenticated user.
    """
    from backend.application.exceptions import UserNotFoundError

    if UUID(user_id) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    user = repo.find_by_id(UUID(user_id))
    if user is None:
        raise UserNotFoundError(user_id)
    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        whatsapp_enabled=user.whatsapp_enabled,
        created_at=user.created_at,
    )
