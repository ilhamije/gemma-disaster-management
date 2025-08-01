from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List
from .extensions import db

class AnalysisResult(db.Model):
    __tablename__ = "analysis_results"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String, nullable=False)
    image_filename = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    center_lat = db.Column(db.Float, nullable=True)
    center_lon = db.Column(db.Float, nullable=True)
    processing_status = db.Column(db.String, nullable=False)

    polygons = db.relationship("PolygonFeature", back_populates="result", cascade="all, delete-orphan")


class PolygonFeature(db.Model):
    __tablename__ = "polygon_features"

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey("analysis_results.id"), nullable=False)
    polygon_id = db.Column(db.String, nullable=False)
    damage_type = db.Column(db.String)
    confidence = db.Column(db.Float)
    class_label = db.Column(db.String)
    notes = db.Column(db.String)
    coordinates = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    result = db.relationship("AnalysisResult", back_populates="polygons")


class PolygonJSON(db.Model):
    __tablename__ = "polygon_json"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    geojson = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
