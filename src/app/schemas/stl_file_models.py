from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ============================
# UploadedModel Schemas
# ============================

class UploadedModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    file_name: str
    file_type: str
    file_size: str
    description: Optional[str]
    web_link: Optional[str]
    tags: List[str] = []
    thumbnail: Optional[str]
    project_name: Optional[str]
    designer: Optional[str]
    revision: Optional[str]
    units: Optional[str] = "meters"
    scale_factor: Optional[float] = 1.0
    fluid_density: Optional[float] = 1.225
    fluid_viscosity: Optional[float] = 1.81e-5
    velocity_inlet: Optional[float]
    temperature_inlet: Optional[float]
    pressure_outlet: Optional[float]


class UploadedModelCreate(UploadedModelBase):
    created_by_user_id: int


class UploadedModelUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]


class UploadedModelDelete(BaseModel):
    is_deleted: bool
    deleted_at: Optional[datetime]


class UploadedModelRead(UploadedModelBase):
    id: int
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime]


# ============================
# Component Schemas
# ============================

class ComponentBase(BaseModel):
    name: str
    type: Optional[str] = None
    material: Optional[str] = None


class ComponentCreate(ComponentBase):
    model_id: int


class ComponentUpdate(BaseModel):
    name: Optional[str]
    type: Optional[str]
    material: Optional[str]


class ComponentDelete(BaseModel):
    is_deleted: bool
    deleted_at: Optional[datetime]


class ComponentRead(ComponentBase):
    id: int
    model_id: int
    created_at: datetime
    updated_at: datetime


# ============================
# Analysis Result Schemas
# ============================

class AnalysisResultBase(BaseModel):
    component_id: int
    result_data: Dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = "pending"


class AnalysisResultCreate(AnalysisResultBase):
    pass


class AnalysisResultUpdate(BaseModel):
    result_data: Optional[Dict[str, Any]]
    status: Optional[str]


class AnalysisResultDelete(BaseModel):
    is_deleted: bool
    deleted_at: Optional[datetime]


class AnalysisResultRead(AnalysisResultBase):
    id: int
    created_at: datetime
    updated_at: datetime


# ============================
# Response Schemas
# ============================

class ModelResponse(BaseModel):
    success: bool
    message: str
    data: Optional[UploadedModelRead]


class ModelsListResponse(BaseModel):
    success: bool
    data: List[UploadedModelRead]
    total: int


class ComponentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ComponentRead]


class ComponentsListResponse(BaseModel):
    success: bool
    data: List[ComponentRead]
    total: int


class AnalysisResponse(BaseModel):
    success: bool
    message: str
    data: Optional[AnalysisResultRead]


class AnalysisListResponse(BaseModel):
    success: bool
    data: List[AnalysisResultRead]
    total: int
