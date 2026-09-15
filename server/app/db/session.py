from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.configs.settings import settings, SERVER_DIR, ensure_directories

# Ensure database and upload folders exist
ensure_directories()

# SQLite engine configuration
db_path = settings.DATABASE_URL
if db_path.startswith("sqlite:///./"):
    # Convert relative path to absolute server path for reliability
    relative_part = db_path.replace("sqlite:///./", "")
    db_path = f"sqlite:///{SERVER_DIR}/{relative_part}"

engine = create_engine(
    db_path,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
