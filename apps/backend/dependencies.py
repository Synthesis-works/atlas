from collections.abc import Generator

import jwt
from atlas_db.core.session import SessionLocal
from atlas_db.models.core import MembershipStatus, User
from atlas_db.repositories.core import (
    InvitationRepository,
    OrganizationMemberRepository,
    OrganizationRepository,
    ProjectRepository,
    UserRepository,
)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from apps.backend.config import settings
from apps.backend.schemas.organizations import OrganizationMemberRead
from apps.backend.services.auth import AuthService
from apps.backend.services.organizations import OrganizationService
from apps.backend.services.projects import ProjectService

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
        invite_repo=InvitationRepository(db),
    )


def get_project_service(db: Session = Depends(get_db_session)) -> ProjectService:
    return ProjectService(project_repo=ProjectRepository(db))


def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(user_repo=UserRepository(db))


from atlas_db.repositories.dataset import DatasetRepository, DatasetVersionRepository

from apps.backend.services.benchmarks import BenchmarkService
from apps.backend.services.datasets import DatasetService
from apps.backend.services.publishing import PublishingService


def get_dataset_service(db: Session = Depends(get_db_session)) -> DatasetService:
    return DatasetService(
        dataset_repo=DatasetRepository(db), version_repo=DatasetVersionRepository(db)
    )


def get_benchmark_service(db: Session = Depends(get_db_session)) -> BenchmarkService:
    return BenchmarkService(db)


def get_publishing_service(db: Session = Depends(get_db_session)) -> PublishingService:
    return PublishingService(version_repo=DatasetVersionRepository(db))


from atlas_db.repositories.authoring import (
    BenchmarkCategoryRepository,
    BenchmarkLifecycleRepository,
    BenchmarkRepository,
    BenchmarkVersionRepository,
    CapabilityRepository,
)
from atlas_db.services.benchmark_service import BenchmarkService

from apps.backend.services.benchmarks import BenchmarkApplicationService


def get_benchmark_app_service(db: Session = Depends(get_db_session)) -> BenchmarkApplicationService:
    benchmark_repo = BenchmarkRepository(db)
    lifecycle_repo = BenchmarkLifecycleRepository(db)
    version_repo = BenchmarkVersionRepository(db)
    category_repo = BenchmarkCategoryRepository(db)
    capability_repo = CapabilityRepository(db)

    domain_service = BenchmarkService(
        benchmark_repo=benchmark_repo, lifecycle_repo=lifecycle_repo, version_repo=version_repo
    )

    return BenchmarkApplicationService(
        domain_service=domain_service,
        benchmark_repo=benchmark_repo,
        category_repo=category_repo,
        capability_repo=capability_repo,
    )


from apps.backend.schemas.auth import TokenClaims


def require_authenticated(token: HTTPAuthorizationCredentials = Depends(security)) -> TokenClaims:
    try:
        payload = jwt.decode(
            token.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
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
    claims: TokenClaims = Depends(require_authenticated), db: Session = Depends(get_db_session)
) -> User:
    user_repo = UserRepository(db)
    user = user_repo.get(claims.sub)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return user


def get_current_member(
    claims: TokenClaims = Depends(require_authenticated), db: Session = Depends(get_db_session)
) -> OrganizationMemberRead:
    # Basic fallback check for active membership when we aren't enforcing via org_id
    if not claims.membership_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    member_repo = OrganizationMemberRepository(db)
    member = member_repo.get(claims.membership_id)
    if not member or member.status != MembershipStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid membership")
    return OrganizationMemberRead.model_validate(member)


from services.report.core.cache import NoopReportCache
from services.report.repositories.reporting_repo import ReportingRepository
from services.report.services.queries import (
    CapabilityQueryService,
    HistoryQueryService,
    LeaderboardQueryService,
    RunQueryService,
)
from services.report.services.reporting import ReportingService


def get_reporting_service(db: Session = Depends(get_db_session)) -> ReportingService:
    repo = ReportingRepository(db)
    return ReportingService(
        cache=NoopReportCache(),
        capability_query=CapabilityQueryService(repo),
        leaderboard_query=LeaderboardQueryService(repo),
        history_query=HistoryQueryService(repo),
        run_query=RunQueryService(repo),
    )


from services.search.providers.benchmark import BenchmarkSearchProvider
from services.search.providers.execution import ExecutionSearchProvider
from services.search.registry import SearchRegistry
from services.search.service import SearchService


def get_search_service(db: Session = Depends(get_db_session)) -> SearchService:
    registry = SearchRegistry()
    registry.register(BenchmarkSearchProvider(db))
    registry.register(ExecutionSearchProvider(db))
    return SearchService(registry)


from apps.backend.services.executions import ExecutionApplicationService
from atlas_db.repositories.execution import ExecutionRepository


def get_execution_app_service(db: Session = Depends(get_db_session)) -> ExecutionApplicationService:
    repo = ExecutionRepository(db)
    return ExecutionApplicationService(execution_repo=repo)


from apps.backend.services.leaderboard import LeaderboardApplicationService
from packages.database.atlas_db.repositories.leaderboard import LeaderboardRepository


def get_leaderboard_app_service(
    db: Session = Depends(get_db_session),
) -> LeaderboardApplicationService:
    leaderboard_repo = LeaderboardRepository(db)
    benchmark_version_repo = BenchmarkVersionRepository(db)
    capability_repo = CapabilityRepository(db)
    return LeaderboardApplicationService(
        leaderboard_repo=leaderboard_repo,
        benchmark_version_repo=benchmark_version_repo,
        capability_repo=capability_repo,
    )
