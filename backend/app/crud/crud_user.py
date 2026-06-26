import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for the User model.

    Adds user-specific methods like email lookups and duplicate checks.
    """

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Find a user by their email address.

        Args:
            db: Database session.
            email: The email to search for.

        Returns:
            User instance or None if no match.
        """
        return db.query(User).filter(User.email == email).first()

    def is_email_taken(self, db: Session, *, email: str) -> bool:
        """Check whether an email address is already registered.

        Used during registration to prevent duplicate accounts.
        """
        return db.query(User).filter(User.email == email).first() is not None

    def create_with_hash(self, db: Session, *, obj_in: UserCreate, password_hash: str) -> User:
        """Create a new user with a pre-hashed password.

        The controller layer computes the hash; this method stores it.
        """
        db_obj = User(
            full_name=obj_in.full_name,
            email=obj_in.email,
            password_hash=password_hash,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logger.info("Created user id=%s email=%s", db_obj.id, db_obj.email)
        return db_obj

    def deactivate(self, db: Session, *, id: str) -> Optional[User]:
        """Soft-delete a user by setting is_active to False.

        Preserves all related data while preventing login.
        """
        user = self.get(db, id=id)
        if user:
            user.is_active = False
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("Deactivated user id=%s", id)
        return user


user = CRUDUser(User)
