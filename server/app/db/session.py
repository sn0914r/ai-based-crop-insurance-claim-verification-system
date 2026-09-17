from sqlalchemy import create_engine, text
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

    # Automatically add new columns if upgrading existing SQLite database
    try:
        with engine.connect() as conn:
            # Check claims columns
            claim_info = conn.execute(text("PRAGMA table_info(claims)")).fetchall()
            claim_cols = [row[1] for row in claim_info]
            if "latitude" not in claim_cols:
                conn.execute(text("ALTER TABLE claims ADD COLUMN latitude REAL"))
            if "longitude" not in claim_cols:
                conn.execute(text("ALTER TABLE claims ADD COLUMN longitude REAL"))
            if "incident_date" not in claim_cols:
                conn.execute(text("ALTER TABLE claims ADD COLUMN incident_date TEXT"))

            # Check claim_assessments columns
            assessment_info = conn.execute(text("PRAGMA table_info(claim_assessments)")).fetchall()
            assessment_cols = [row[1] for row in assessment_info]
            if "weather_score" not in assessment_cols:
                conn.execute(text("ALTER TABLE claim_assessments ADD COLUMN weather_score REAL"))
            if "damage_cause" not in assessment_cols:
                conn.execute(text("ALTER TABLE claim_assessments ADD COLUMN damage_cause TEXT"))
            if "weather_details" not in assessment_cols:
                conn.execute(text("ALTER TABLE claim_assessments ADD COLUMN weather_details TEXT"))
            conn.commit()
    except Exception:
        pass
