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
        return query.first()  # type: ignore

    def get_by(self, include_archived: bool = False, **kwargs: Any) -> ModelType | None:
        query = self.db.query(self.model).filter_by(**kwargs)
        if not include_archived and hasattr(self.model, "archived_at"):
            query = query.filter(self.model.archived_at.is_(None))
        return query.first()  # type: ignore

    def list(self, include_archived: bool = False, **kwargs: Any) -> list[ModelType]:
        query = self.db.query(self.model).filter_by(**kwargs)
        if not include_archived and hasattr(self.model, "archived_at"):
            query = query.filter(self.model.archived_at.is_(None))
        return query.all()  # type: ignore

    def create(self, obj_in: Any = None, *, commit: bool = True, **kwargs: Any) -> ModelType:
        if obj_in is None:
            obj_in = kwargs.pop("obj_in", None)

        if obj_in is not None:
            if isinstance(obj_in, self.model):
                obj = obj_in
            elif isinstance(obj_in, dict):
                obj_in.update(kwargs)
                obj = self.model(**obj_in)
            else:
                obj = obj_in
        else:
            obj = self.model(**kwargs)

        self.db.add(obj)
        if commit:
            self.db.commit()
            try:
                self.db.refresh(obj)
            except Exception:
                pass
        else:
            self.db.flush()
        return obj  # type: ignore

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
        return obj  # type: ignore
