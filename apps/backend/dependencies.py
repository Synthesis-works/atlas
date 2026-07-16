from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
import jwt

from atlas_db.core.session import SessionLocal
from atlas_db.repositories.core import (
    OrganizationRepository, OrganizationMemberRepository, 
    InvitationRepository, ProjectRepository, UserRepository
)
from atlas_db.models.core import User, OrganizationRole, MembershipStatus
from apps.backend.services.organizations import OrganizationService
from apps.backend.services.projects import ProjectService
from apps.backend.services.auth import AuthService
from apps.backend.schemas.organizations import OrganizationMemberRead
from apps.backend.config import settings

security = HTTPBearer()

def get_db_session() -> Generator[Session, None, None]:
    """Dependency to provide a database session to API routes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_org_service(db: Session = Depends(get_db_session)) -> OrganizationService:
    return OrganizationService(
        org_repo=OrganizationRepository(db),
        member_repo=OrganizationMemberRepository(db),
        invite_repo=InvitationRepository(db)
    )

def get_project_service(db: Session = Depends(get_db_session)) -> ProjectService:
    return ProjectService(project_repo=ProjectRepository(db))

def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(user_repo=UserRepository(db))

from apps.backend.schemas.auth import TokenClaims

def require_authenticated(token: HTTPAuthorizationCredentials = Depends(security)) -> TokenClaims:
    try:
        payload = jwt.decode(token.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenClaims(**payload)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        # Pydantic validation error or similar
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session)
) -> User:
    user_repo = UserRepository(db)
    user = user_repo.get(claims.sub)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        
    return user

def get_current_member(
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session)
) -> OrganizationMemberRead:
    # Basic fallback check for active membership when we aren't enforcing via org_id
    if not claims.membership_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
        
    member_repo = OrganizationMemberRepository(db)
    member = member_repo.get(claims.membership_id)
    if not member or member.status != MembershipStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid membership")
    return OrganizationMemberRead.model_validate(member)
