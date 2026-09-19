from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, index=True)
    video_path = Column(String(512), nullable=False)
    video_name = Column(String(256), nullable=False)
    status = Column(String(32), default="queued") # queued, processing, completed, failed
    progress = Column(Float, default=0.0)
    status_message = Column(String(256), default="Waiting in queue")
    total_events = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    config_json = Column(Text, default="{}")

class EventModel(Base):
    __tablename__ = "events"

    id = Column(String(64), primary_key=True, index=True)
    job_id = Column(String(64), ForeignKey("jobs.id"), nullable=True)
    video_id = Column(String(256), nullable=False)
    timestamp_start = Column(Float, default=0.0)
    timestamp_peak = Column(Float, nullable=False)
    timestamp_end = Column(Float, default=0.0)
    participant_ids = Column(Text, default="[]") # JSON list of IDs
    participant_classes = Column(Text, default="[]") # JSON list of class strings
    conflict_type = Column(String(64), default="rear_end")
    min_ttc = Column(Float, nullable=True)
    pet = Column(Float, nullable=True)
    max_drac = Column(Float, nullable=True)
    delta_v = Column(Float, default=0.0)
    min_distance_m = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(32), default="medium")
    status = Column(String(32), default="reliable") # reliable vs uncertain
    tracking_confidence = Column(Float, default=0.9)
    uncertainty_reasons = Column(Text, default="[]") # JSON list
    road_zone = Column(String(128), default="General Area")
    ground_coords = Column(Text, default="[0, 0]") # JSON [X, Y]
    pixel_coords = Column(Text, default="[0, 0]") # JSON [u, v]
    evidence_clip_path = Column(String(512), nullable=True)
    recommendation_summary = Column(Text, default="")
    engineering_action = Column(Text, default="")
    policy_action = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    reviews = relationship("HumanReviewModel", back_populates="event", cascade="all, delete-orphan")

class HumanReviewModel(Base):
    __tablename__ = "human_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), ForeignKey("events.id"), nullable=False, index=True)
    reviewer_id = Column(String(64), default="analyst_default")
    decision = Column(String(32), default="pending") # approved, rejected, modified
    notes = Column(Text, default="")
    reviewed_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("EventModel", back_populates="reviews")

class ZoneConfigModel(Base):
    __tablename__ = "zone_configs"

    id = Column(String(64), primary_key=True)
    config_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
