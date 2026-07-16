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

def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> User:
    try:
        payload = jwt.decode(token.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_repo = UserRepository(db)
    user = user_repo.get(UUID(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        
    return user

def get_current_member(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> OrganizationMemberRead:
    # Slice 3A only implements basic identity. We will just decode the token 
    # to see if it carries a membership_id, or return a fake/error one until Slice 3B is built.
    # To keep the previous tests running, we will implement the minimum viable here or 
    # extract the membership if provided in the token. 
    
    # Let's decode the token
    try:
        payload = jwt.decode(token.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        membership_id = payload.get("membership_id")
        # In Slice 3B we will look this up properly and enforce roles.
        # For now, to keep the current API shape running if tested:
        if membership_id:
            member_repo = OrganizationMemberRepository(db)
            member = member_repo.get(UUID(membership_id))
            if not member:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid membership")
            return OrganizationMemberRead.model_validate(member)
        else:
            # Fallback for now if the token doesn't have a membership
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
