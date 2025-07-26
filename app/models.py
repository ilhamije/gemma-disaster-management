from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List
from .extensions import db


class AnalysisResult(db.Model):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(default="")  # Add batch tracking
    image_filename: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    center_lat: Mapped[float] = mapped_column(nullable=True)
    center_lon: Mapped[float] = mapped_column(nullable=True)
    processing_status: Mapped[str] = mapped_column(default="pending")  # pending, processing, completed, failed

    polygons: Mapped[List["PolygonFeature"]] = relationship("PolygonFeature", back_populates="result", cascade="all, delete-orphan")


class PolygonFeature(db.Model):
    __tablename__ = "polygon_features"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id"))
    polygon_id: Mapped[str]
    damage_type: Mapped[str]
    confidence: Mapped[float]
    class_label: Mapped[str]
    notes: Mapped[str]

    coordinates: Mapped[str]  # stored as JSON stringified coordinates

    result: Mapped["AnalysisResult"] = relationship("AnalysisResult", back_populates="polygons")
