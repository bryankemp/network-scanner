"""
Database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from .config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency function to get database session.
    Usage: Depends(get_db) in FastAPI endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables and create default admin user.
    """

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create default admin user if not exists
    db = SessionLocal()
    try:
        from .models.user import User
        from .auth.security import get_password_hash

        admin_user = db.query(User).filter(User.username == settings.default_admin_username).first()
        if not admin_user:
            admin_user = User(
                username=settings.default_admin_username,
                hashed_password=get_password_hash(settings.default_admin_password),
                role="admin",
                must_change_password=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"✓ Default admin user created: {settings.default_admin_username}")
        else:
            print(f"✓ Admin user already exists: {settings.default_admin_username}")
    finally:
        db.close()
