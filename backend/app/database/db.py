from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from .models import Base, JobModel
from ..settings import DB_PATH
from datetime import datetime

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    with SessionLocal() as db:
        yield db

def init_db():
    Base.metadata.create_all(bind=engine)
    # Additive migration preserves existing jobs and reviews.
    columns = {c["name"] for c in inspect(engine).get_columns("jobs")}
    with engine.begin() as connection:
        if "config_json" not in columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN config_json TEXT DEFAULT '{}'"))
        connection.execute(text("PRAGMA journal_mode=WAL"))
    with SessionLocal() as db:
        for job in db.query(JobModel).filter(JobModel.status.in_(["queued", "processing"])).all():
            job.status = "failed"
            job.status_message = "Processing was interrupted by a server restart. Submit the video again."
            job.completed_at = datetime.utcnow()
        db.commit()
    # Never insert labelled or preset incidents into an empty database.
