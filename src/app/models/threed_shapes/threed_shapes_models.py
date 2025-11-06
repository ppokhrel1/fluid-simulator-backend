# app/models/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional

class PrimitiveRequest(BaseModel):
    shape_type: str  # 'cube', 'sphere', 'cylinder', 'cone', 'torus'
    parameters: Dict
    position: Optional[List[float]] = [0, 0, 0]
    rotation: Optional[List[float]] = [0, 0, 0]

class BooleanOperationRequest(BaseModel):
    operation: str  # 'union', 'difference', 'intersection'
    mesh_a_id: str
    mesh_b_id: str

class AIGenerationRequest(BaseModel):
    prompt: str
    base_mesh_id: Optional[str] = None
    operation: Optional[str] = "add"

class TransformRequest(BaseModel):
    mesh_id: str
    position: List[float]
    rotation: List[float]
    scale: List[float]

class ExportRequest(BaseModel):
    format: str = "stl"
    user_id: str

class MeshResponse(BaseModel):
    mesh_id: str
    vertices: List[List[float]]
    faces: List[List[int]]
    type: str
    position: List[float]

class ExportResponse(BaseModel):
    download_url: str
    mesh_id: str
    format: str
    user_id: str

class MeshRemediationRequest(BaseModel):
    mesh_id: str
    operation: str  # 'decimate', 'smooth', 'remesh'
    parameters: Dict = {}

class MeshRemediationResponse(BaseModel):
    mesh_id: str
    vertices: List[List[float]]
    faces: List[List[int]]
    operation: str
    original_vertex_count: int
    new_vertex_count: int
    original_face_count: int
    new_face_count: int
