import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.database import Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic base class for CRUD operations on SQLAlchemy models.

    Provides standard Create, Read, Update, Delete, pagination, and filtering
    methods. Subclass per-model and add domain-specific query methods.

    Type parameters:
        ModelType: The SQLAlchemy model class.
        CreateSchemaType: Pydantic schema for creation payloads.
        UpdateSchemaType: Pydantic schema for partial-update payloads.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record from a Pydantic schema.

        Converts the schema to a dict and instantiates the ORM model.
        Logs the operation for auditability.
        """
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logger.info("Created %s with id=%s", self.model.__name__, db_obj.id)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[ModelType]:
        """Retrieve a single record by its UUID primary key.

        Returns None when no record matches (does NOT raise).
        """
        obj = db.query(self.model).filter(self.model.id == id).first()
        if obj:
            logger.debug("Fetched %s id=%s", self.model.__name__, id)
        else:
            logger.debug("%s id=%s not found", self.model.__name__, id)
        return obj

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        descending: bool = True,
    ) -> List[ModelType]:
        """Retrieve a paginated list of records.

        Args:
            skip: Number of records to skip (offset).
            limit: Maximum records to return (page size).
            order_by: Column name to sort by (None = no ordering).
            descending: Sort descending when True, ascending when False.

        Returns:
            List of model instances.
        """
        query = db.query(self.model)
        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                query = query.order_by(desc(column) if descending else column)
        return query.offset(skip).limit(limit).all()

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """Patch an existing record with new field values.

        Accepts either a Pydantic schema or a raw dict. Only the fields
        present in the input are updated — others are left untouched.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logger.info("Updated %s id=%s", self.model.__name__, db_obj.id)
        return db_obj

    def remove(self, db: Session, *, id: str) -> Optional[ModelType]:
        """Delete a record by its UUID primary key.

        Returns the deleted object (so callers can inspect it), or None
        if the record did not exist.
        """
        obj = db.query(self.model).filter(self.model.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            logger.info("Deleted %s id=%s", self.model.__name__, id)
        else:
            logger.warning("Attempted delete of non-existent %s id=%s", self.model.__name__, id)
        return obj

    def count(self, db: Session, **filters: Any) -> int:
        """Count records matching optional filter conditions.

        Example: crud_user.count(db, is_active=True)
        """
        query = db.query(self.model)
        for field, value in filters.items():
            column = getattr(self.model, field, None)
            if column is not None:
                query = query.filter(column == value)
        return query.count()

    def get_by_field(
        self, db: Session, field: str, value: Any, unique: bool = False
    ) -> Union[Optional[ModelType], List[ModelType]]:
        """Search records by any column value.

        Args:
            field: Column name to filter on.
            value: Value to match.
            unique: If True, return a single record (or None). If False,
                    return a list (may be empty).

        Returns:
            Single model instance when unique=True, list otherwise.
        """
        column = getattr(self.model, field, None)
        if column is None:
            logger.error("Field '%s' does not exist on %s", field, self.model.__name__)
            return None if unique else []

        query = db.query(self.model).filter(column == value)
        if unique:
            return query.first()
        return query.all()
