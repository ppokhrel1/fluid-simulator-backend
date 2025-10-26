from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Boolean, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class UploadedModel(Base):
    __tablename__ = "models"

    # Match SQL: id UUID DEFAULT gen_random_uuid() PRIMARY KEY
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    
    # Use Text to map to TEXT
    name = Column(Text, nullable=False)
    file_name = Column(Text, nullable=False)
    file_size = Column(Text, nullable=False)
    file_type = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    web_link = Column(Text, nullable=True)
    
    # FIX: Change from Column(JSON) to Column(ARRAY(Text)) to match TEXT[]
    # Match SQL: tags TEXT[] DEFAULT '{}'
    tags = Column(ARRAY(Text), default=[]) 
    
    thumbnail = Column(Text, nullable=True)
    analysis_status = Column(Text, default='pending')
    
    # Engineering metadata
    project_name = Column(Text, nullable=True)
    designer = Column(Text, nullable=True)
    revision = Column(Text, nullable=True)
    units = Column(Text, default="meters")
    scale_factor = Column(Float, default=1.0)
    # Match SQL: bounding_box JSONB
    bounding_box = Column(JSONB, nullable=True)
    total_volume = Column(Float, nullable=True)
    total_surface_area = Column(Float, nullable=True)
    
    # Analysis parameters
    fluid_density = Column(Float, default=1.225)
    fluid_viscosity = Column(Float, default=1.81e-5)
    velocity_inlet = Column(Float, nullable=True)
    temperature_inlet = Column(Float, nullable=True)
    pressure_outlet = Column(Float, nullable=True)
    
    # Match SQL: TIMESTAMPTZ
    upload_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_opened = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_by_user_id = Column(Integer, nullable=False)
    
    components = relationship("Component", back_populates="model")


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    material = Column(String, nullable=True)
    model_id = Column(Integer, ForeignKey("models.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    model = relationship("UploadedModel", back_populates="components")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    component_id = Column(Integer, ForeignKey("components.id"))
    result_data = Column(JSON, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
