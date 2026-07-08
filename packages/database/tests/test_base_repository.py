import pytest
from atlas_db.models.core import User
from atlas_db.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

def test_base_repository_crud(session):
    repo = UserRepository()
    
    # Test Create
    user = repo.create(session, obj_in={
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True
    })
    assert user.id is not None
    assert user.email == "test@example.com"
    
    # Test Get
    fetched = repo.get(session, user.id)
    assert fetched is not None
    assert fetched.id == user.id
    
    # Test Update
    updated = repo.update(session, db_obj=fetched, obj_in={"full_name": "Updated User"})
    assert updated.full_name == "Updated User"
    
    # Test Delete
    deleted = repo.delete(session, id=user.id)
    assert deleted is not None
    assert deleted.id == user.id
    
    assert repo.get(session, user.id) is None
