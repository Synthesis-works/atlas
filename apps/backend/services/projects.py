from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from atlas_db.repositories.core import ProjectRepository
from atlas_db.models.core import Project
from apps.backend.schemas.projects import ProjectCreate

class ProjectService:
    def __init__(self, project_repo: ProjectRepository):
        self.project_repo = project_repo

    def list_for_org(self, org_id: UUID) -> List[Project]:
        return self.project_repo.db.query(Project).filter(Project.org_id == org_id).all()

    def create(self, org_id: UUID, member_id: UUID, data: ProjectCreate) -> Project:
        # We handle unique constraint explicitly for clear error messages, or rely on IntegrityError
        existing = self.project_repo.db.query(Project).filter(Project.org_id == org_id, Project.name == data.name).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Project with name '{data.name}' already exists in this organization")

        try:
            return self.project_repo.create(obj_in={
                "name": data.name,
                "slug": data.slug,
                "description": data.description,
                "org_id": org_id,
                "created_by_member_id": member_id,
                "updated_by_member_id": member_id
            })
        except IntegrityError:
            self.project_repo.db.rollback()
            raise HTTPException(status_code=409, detail="Project with this name already exists")

    def get(self, project_id: UUID) -> Optional[Project]:
        return self.project_repo.get(project_id)
