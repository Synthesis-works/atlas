from sqlalchemy.orm import Session
from .base import BaseRepository
from atlas_db.models.core import Organization, User, Project, Configuration, ConfigurationVersion

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
