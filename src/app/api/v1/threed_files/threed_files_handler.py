# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import os
from src.app.api.services.ai_generate import AIGenerationService
from src.app.api.services.composition_engine import CompositionEngine
from src.app.api.services.supabase_storage import SupabaseStorage
import trimesh
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from src.app.models.threed_shapes.threed_shapes_models import MeshResponse, PrimitiveRequest, BooleanOperationRequest, AIGenerationRequest, TransformRequest, ExportRequest, ExportResponse

# from app.services.composition_engine import CompositionEngine
# from app.services.ai_generation import AIGenerationService
# from app.services.supabase_storage import SupabaseStorage

router = APIRouter(prefix="/developer", tags=["Advanced 3D Object Studio"])



# Initialize services
composition_engine = CompositionEngine()
ai_service = AIGenerationService()
supabase_storage = SupabaseStorage()

# In-memory storage for meshes (in production, use a database)
meshes_store: Dict[str, Dict] = {}



@router.post("/object-studio/primitives/create", response_model=MeshResponse)
async def create_primitive(request: PrimitiveRequest):
    """Create a primitive shape"""
    try:
        mesh = composition_engine.create_primitive(
            request.shape_type, 
            request.parameters
        )
        
        mesh_id = str(uuid.uuid4())
        meshes_store[mesh_id] = {
            'mesh': mesh,
            'position': request.position,
            'rotation': request.rotation,
            'scale': [1.0, 1.0, 1.0],
            'type': 'primitive',
            'user_id': "default"  # In production, get from auth
        }
        
        return MeshResponse(
            mesh_id=mesh_id,
            vertices=mesh.vertices.tolist(),
            faces=mesh.faces.tolist(),
            type=request.shape_type,
            position=request.position
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/object-studio/boolean/operation", response_model=MeshResponse)
async def boolean_operation(request: BooleanOperationRequest):
    """Perform boolean operations between two meshes"""
    try:
        if request.mesh_a_id not in meshes_store or request.mesh_b_id not in meshes_store:
            raise HTTPException(status_code=404, detail="Mesh not found")
        
        mesh_a = meshes_store[request.mesh_a_id]['mesh']
        mesh_b = meshes_store[request.mesh_b_id]['mesh']
        
        result_mesh = composition_engine.boolean_operation(
            mesh_a, mesh_b, request.operation
        )
        
        result_id = str(uuid.uuid4())
        meshes_store[result_id] = {
            'mesh': result_mesh,
            'position': [0, 0, 0],
            'rotation': [0, 0, 0],
            'scale': [1.0, 1.0, 1.0],
            'type': 'boolean_result'
        }
        
        return MeshResponse(
            mesh_id=result_id,
            vertices=result_mesh.vertices.tolist(),
            faces=result_mesh.faces.tolist(),
            type='boolean',
            position=[0, 0, 0]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/object-studio/ai/generate-shape", response_model=MeshResponse)
async def generate_ai_shape(request: AIGenerationRequest):
    """Generate a 3D shape using AI from text prompt"""
    try:
        base_mesh_data = None
        if request.base_mesh_id and request.base_mesh_id in meshes_store:
            base_mesh_data = meshes_store[request.base_mesh_id]
        
        result = await ai_service.generate_shape_from_prompt(
            request.prompt, 
            base_mesh_data
        )
        
        mesh_id = str(uuid.uuid4())
        
        # Convert the result dict back to a trimesh object for storage
        temp_engine = CompositionEngine()
        
        # For AI-generated meshes, we store the actual mesh data
        # In a real implementation, you'd reconstruct the mesh from vertices/faces
        meshes_store[mesh_id] = {
            'mesh_data': result,  # Store the raw data
            'position': result.get('position', [0, 0, 0]),
            'rotation': [0, 0, 0],
            'scale': [1.0, 1.0, 1.0],
            'type': 'ai_generated',
            'prompt': request.prompt
        }
        
        return MeshResponse(
            mesh_id=mesh_id,
            vertices=result["vertices"],
            faces=result["faces"],
            type=result["type"],
            position=result.get("position", [0, 0, 0])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

@router.post("/object-studio/transform/update")
async def update_transform(request: TransformRequest):
    """Update mesh transformation"""
    if request.mesh_id not in meshes_store:
        raise HTTPException(status_code=404, detail="Mesh not found")
    
    meshes_store[request.mesh_id].update({
        'position': request.position,
        'rotation': request.rotation,
        'scale': request.scale
    })
    
    return {"status": "success", "message": "Transform updated"}

@router.post("/object-studio/export/{mesh_id}", response_model=ExportResponse)
async def export_mesh(mesh_id: str, request: ExportRequest):
    """Export mesh and store in Supabase"""
    if mesh_id not in meshes_store:
        raise HTTPException(status_code=404, detail="Mesh not found")
    
    mesh_data = meshes_store[mesh_id]
    
    try:
        # Reconstruct the mesh from stored data
        
        if 'mesh' in mesh_data:
            # For primitive meshes
            mesh = mesh_data['mesh']
        else:
            # For AI-generated meshes, create mesh from vertices/faces
            vertices = mesh_data['mesh_data']['vertices']
            faces = mesh_data['mesh_data']['faces']
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Store in Supabase and get public URL
        public_url = await supabase_storage.store_mesh(
            mesh, mesh_id, request.format
        )
        
        return ExportResponse(
            download_url=public_url,
            mesh_id=mesh_id,
            format=request.format,
            user_id=request.user_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/object-studio/meshes")
async def get_all_meshes():
    """Get all current meshes for the user"""
    # In production, filter by user_id from auth
    result = {}
    for mesh_id, data in meshes_store.items():
        vertex_count = 0
        face_count = 0
        
        if 'mesh' in data:
            vertex_count = len(data['mesh'].vertices)
            face_count = len(data['mesh'].faces)
        elif 'mesh_data' in data:
            vertex_count = len(data['mesh_data']['vertices'])
            face_count = len(data['mesh_data']['faces'])
        
        result[mesh_id] = {
            "type": data['type'],
            "position": data['position'],
            "rotation": data['rotation'],
            "scale": data['scale'],
            "vertex_count": vertex_count,
            "face_count": face_count
        }
    return result

@router.delete("/object-studio/meshes/{mesh_id}")
async def delete_mesh(mesh_id: str):
    """Delete a mesh"""
    if mesh_id in meshes_store:
        del meshes_store[mesh_id]
        return {"status": "deleted", "message": f"Mesh {mesh_id} deleted"}
    raise HTTPException(status_code=404, detail="Mesh not found")

# # Error handlers
# @router.exception_handler(HTTPException)
# async def http_exception_handler(request, exc):
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"detail": exc.detail}
#     )

# @router.exception_handler(Exception)
# async def general_exception_handler(request, exc):
#     return JSONResponse(
#         status_code=500,
#         content={"detail": f"Internal server error: {str(exc)}"}
#     )
