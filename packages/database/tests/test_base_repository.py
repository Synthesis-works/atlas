from atlas_db.models.core import User
from atlas_db.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    model = User

def test_base_repository_crud(session):
    repo = UserRepository(session)
    
    # Test Create
    user = repo.create(obj_in={
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True
    })
    assert user.id is not None
    assert user.email == "test@example.com"
    
    # Test Get
    fetched = repo.get(user.id)
    assert fetched is not None
    assert fetched.id == user.id
    
    # Test Update
    updated = repo.update(db_obj=fetched, obj_in={"full_name": "Updated User"})
    assert updated.full_name == "Updated User"
    
    # Test Delete (Soft Delete)
    deleted = repo.delete(id=user.id)
    assert deleted is not None
    assert deleted.id == user.id
    assert deleted.archived_at is not None
    
    # Ensure get() excludes archived by default
    assert repo.get(user.id) is None
    
    # Ensure get(include_archived=True) works
    archived = repo.get(user.id, include_archived=True)
    assert archived is not None
    assert archived.archived_at is not None
