from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Boolean, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.app.core.db.database import Base


class UploadedModel(Base):
    __tablename__ = "uploaded_models"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    name = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(String(50))
    file_type = Column(String(100))
    description = Column(Text)
    web_link = Column(String(500))
    tags = Column(JSON, default=[])
    thumbnail = Column(String(500))
    
    # Engineering metadata
    project_name = Column(String(255))
    designer = Column(String(255))
    revision = Column(String(100))
    units = Column(String(50), default="meters")
    scale_factor = Column(Float, default=1.0)
    
    # Analysis parameters
    fluid_density = Column(Float)
    fluid_viscosity = Column(Float)
    velocity_inlet = Column(Float)
    temperature_inlet = Column(Float)
    pressure_outlet = Column(Float)
    analysis_status = Column(String(50), default='pending')
    
    # Timestamps
    last_opened = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_by_user_id = Column(Integer, ForeignKey("user.id"))
    
    # Relationships
    components = relationship("Component", back_populates="model")
    design_assets = relationship("DesignAsset", back_populates="original_model")
    chat_sessions = relationship("ChatSession", back_populates="model")
    labels = relationship("AssetLabel", back_populates="model")


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("uploaded_models.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    component_type = Column(String(100))
    material = Column(String(255))
    color = Column(String(50))
    dimensions = Column(String(255))
    properties = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    model = relationship("UploadedModel", back_populates="components")
    analysis_results = relationship("AnalysisResult", back_populates="component")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    component_id = Column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    analysis_type = Column(String(100), nullable=False)
    result_data = Column(JSON, nullable=False)
    status = Column(String(50), default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))

    component = relationship("Component", back_populates="analysis_results")
