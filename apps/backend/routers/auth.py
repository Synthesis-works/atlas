from fastapi import APIRouter, Depends, status
from typing import Any

from apps.backend.schemas.auth import UserRegister, UserLogin, TokenResponse, AuthUserRead
from apps.backend.schemas.responses import APIResponse
from apps.backend.services.auth import AuthService
from apps.backend.dependencies import get_auth_service, get_current_user
from atlas_db.models.core import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=APIResponse[AuthUserRead], status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    user = auth_service.register_user(data)
    return APIResponse.success_response(
        data=user,
        message="User registered successfully"
    )

@router.post("/login", response_model=APIResponse[TokenResponse], status_code=status.HTTP_200_OK)
def login(
    data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    token = auth_service.authenticate_user(data)
    return APIResponse.success_response(
        data=token,
        message="Login successful"
    )

@router.get("/me", response_model=APIResponse[AuthUserRead], status_code=status.HTTP_200_OK)
def me(
    current_user: User = Depends(get_current_user)
) -> Any:
    return APIResponse.success_response(
        data=current_user,
        message="User details retrieved successfully"
    )
