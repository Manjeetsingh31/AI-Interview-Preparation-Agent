import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.progress import Progress
from backend.app.schemas.progress import ProgressCreate, ProgressUpdate

logger = logging.getLogger(__name__)


class CRUDProgress(CRUDBase[Progress, ProgressCreate, ProgressUpdate]):
    """CRUD operations for Progress (one-to-one with User).

    Provides convenience methods for the one-to-one relationship.
    """

    def get_by_user(self, db: Session, *, user_id: str) -> Optional[Progress]:
        """Retrieve the single progress record for a user.

        Returns None if the user hasn't completed any interviews yet.
        """
        return db.query(Progress).filter(Progress.user_id == user_id).first()

    def upsert(
        self,
        db: Session,
        *,
        user_id: str,
        obj_in: ProgressUpdate,
    ) -> Progress:
        """Create or update a progress record for the given user.

        If a record already exists it is updated; otherwise a new row
        is inserted. This avoids explicit "does it exist?" checks in
        the service layer.
        """
        existing = self.get_by_user(db, user_id=user_id)
        if existing:
            return self.update(db, db_obj=existing, obj_in=obj_in)

        create_data = obj_in.model_dump(exclude_unset=True)
        create_data["user_id"] = user_id
        db_obj = Progress(**create_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logger.info("Created progress for user id=%s", user_id)
        return db_obj


progress = CRUDProgress(Progress)
