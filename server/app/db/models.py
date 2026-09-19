from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String(50), unique=True, index=True, nullable=False)
    farmer_id = Column(String(50), index=True, nullable=False)
    crop_type = Column(String(50), nullable=False)
    claimed_damage = Column(Float, nullable=False)
    image_path = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    incident_date = Column(String(20), nullable=True)
    field_boundary = Column(Text, nullable=True)
    status = Column(String(50), default="EVALUATING", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    assessments = relationship("ClaimAssessment", back_populates="claim", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="claim", cascade="all, delete-orphan")

    def to_dict(self):
        import json
        parsed_boundary = None
        if self.field_boundary:
            try:
                parsed_boundary = json.loads(self.field_boundary)
            except Exception:
                parsed_boundary = None

        return {
            "id": self.id,
            "claimId": self.claim_id,
            "farmerId": self.farmer_id,
            "cropType": self.crop_type,
            "claimedDamage": self.claimed_damage,
            "imagePath": self.image_path,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "incidentDate": self.incident_date,
            "fieldBoundary": parsed_boundary,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

class ClaimAssessment(Base):
    __tablename__ = "claim_assessments"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String(50), ForeignKey("claims.claim_id"), nullable=False, index=True)
    visual_class = Column(String(50), nullable=False)
    damage_severity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    weather_score = Column(Float, nullable=True)
    damage_cause = Column(String(50), nullable=True)
    weather_details = Column(Text, nullable=True)
    satellite_score = Column(Float, nullable=True)
    damaged_area_percentage = Column(Float, nullable=True)
    satellite_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    claim = relationship("Claim", back_populates="assessments")

    def to_dict(self):
        import json
        parsed_details = None
        if self.weather_details:
            try:
                parsed_details = json.loads(self.weather_details)
            except Exception:
                parsed_details = self.weather_details

        parsed_satellite = None
        if self.satellite_details:
            try:
                parsed_satellite = json.loads(self.satellite_details)
            except Exception:
                parsed_satellite = self.satellite_details

        return {
            "id": self.id,
            "claimId": self.claim_id,
            "visualClass": self.visual_class,
            "damageSeverity": self.damage_severity,
            "confidence": self.confidence,
            "weatherScore": self.weather_score,
            "damageCause": self.damage_cause,
            "weatherDetails": parsed_details,
            "satelliteScore": self.satellite_score,
            "damagedAreaPercentage": self.damaged_area_percentage,
            "satelliteDetails": parsed_satellite,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String(50), ForeignKey("claims.claim_id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    actor = Column(String(50), default="SYSTEM", nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    claim = relationship("Claim", back_populates="audit_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "claimId": self.claim_id,
            "eventType": self.event_type,
            "actor": self.actor,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
