from .base import BaseRepository
from atlas_db.models.core import Organization, User, Project, Configuration, ConfigurationVersion, OrganizationMember, Invitation

class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    model = OrganizationMember

    def get_by_user_and_org(self, user_id, org_id) -> OrganizationMember | None:
        return self.db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.organization_id == org_id
        ).first()

class InvitationRepository(BaseRepository[Invitation]):
    model = Invitation

class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

class ProjectRepository(BaseRepository[Project]):
    model = Project

class ConfigurationRepository(BaseRepository[Configuration]):
    model = Configuration

class ConfigurationVersionRepository(BaseRepository[ConfigurationVersion]):
    model = ConfigurationVersion

class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(self.model).filter(self.model.email == email).first()
