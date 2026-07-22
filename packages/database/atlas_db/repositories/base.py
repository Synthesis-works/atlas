from typing import Any, Generic, TypeVar

from atlas_db.core.base import Base
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id: Any, include_archived: bool = False) -> ModelType | None:
        query = self.db.query(self.model).filter(self.model.id == id)
        if not include_archived and hasattr(self.model, "archived_at"):
            query = query.filter(self.model.archived_at.is_(None))
        return query.first()

    def create(self, *, obj_in: dict, commit: bool = True) -> ModelType:
        obj = self.model(**obj_in)
        self.db.add(obj)
        if commit:
            self.db.commit()
            self.db.refresh(obj)
        else:
            self.db.flush()
        return obj

    def update(self, *, db_obj: ModelType, obj_in: dict, commit: bool = True) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        if commit:
            self.db.commit()
            self.db.refresh(db_obj)
        else:
            self.db.flush()
        return db_obj

    def delete(self, *, id: Any, hard: bool = False, commit: bool = True) -> ModelType | None:
        obj = self.db.get(self.model, id)
        if obj:
            if not hard and hasattr(self.model, "archived_at"):
                from atlas_db.core.base import utcnow

                obj.archived_at = utcnow()
                self.db.add(obj)
            else:
                self.db.delete(obj)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
        return obj
