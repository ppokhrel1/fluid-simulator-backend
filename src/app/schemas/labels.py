"""3D Model Labeling system Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Asset Label Schemas
class AssetLabelBase(BaseModel):
    model_id: int
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    position_z: Optional[float] = None
    text: str
    category: Optional[str] = None  # Material|Part|Function|Texture|Dimension|Other


class LabelCreate(AssetLabelBase):
    pass


class LabelUpdate(BaseModel):
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    position_z: Optional[float] = None
    text: Optional[str] = None
    category: Optional[str] = None


class LabelUpdateInternal(LabelUpdate):
    pass


class LabelDelete(BaseModel):
    pass


class LabelRead(AssetLabelBase):
    id: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# AI Suggestion Schemas
class AILabelSuggestion(BaseModel):
    label_text: str
    category: str
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    suggested_position: dict = Field(..., description="Suggested x,y,z position")
    description: str


class AISuggestionsResponse(BaseModel):
    suggestions: List[AILabelSuggestion]
    model_id: int