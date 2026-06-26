import logging
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)


if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable foreign key enforcement in SQLite.

        SQLite does NOT enforce foreign keys by default. This pragma must be
        issued per-connection to ensure ON DELETE CASCADE works at the DB
        level. Without this, cascade deletes rely solely on SQLAlchemy's ORM.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Create all database tables at application startup.

    Reads the ORM model metadata from Base and issues CREATE TABLE IF NOT EXISTS
    statements for every table that hasn't been created yet. Safe to call
    repeatedly — SQLAlchemy's create_all is idempotent.
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def check_db_connection():
    """Verify the database is reachable by executing a trivial query.

    Returns:
        bool: True if the connection succeeds.

    Raises:
        Exception: Re-raises the underlying connection error after logging.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection is healthy.")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def get_db():
    """FastAPI dependency that yields a database session per request.

    Yields:
        Session: SQLAlchemy ORM session bound to the engine.

    Ensures the session is always closed when the request finishes, preventing
    connection leaks in long-running server processes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
