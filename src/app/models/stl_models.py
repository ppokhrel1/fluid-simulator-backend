from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class UploadedModel(Base):
    __tablename__ = "uploaded_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(String, nullable=False)
    description = Column(String, nullable=True)
    web_link = Column(String, nullable=True)
    tags = Column(JSON, default=[])
    thumbnail = Column(String, nullable=True)
    project_name = Column(String, nullable=True)
    designer = Column(String, nullable=True)
    revision = Column(String, nullable=True)
    units = Column(String, default="meters")
    scale_factor = Column(Float, default=1.0)
    fluid_density = Column(Float, default=1.225)
    fluid_viscosity = Column(Float, default=1.81e-5)
    velocity_inlet = Column(Float, nullable=True)
    temperature_inlet = Column(Float, nullable=True)
    pressure_outlet = Column(Float, nullable=True)
    created_by_user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    components = relationship("Component", back_populates="model")


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    material = Column(String, nullable=True)
    model_id = Column(Integer, ForeignKey("uploaded_models.id"))
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
