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
from ....models.threed_shapes.threed_shapes_models import MeshRemediationRequest, MeshRemediationResponse, MeshResponse, PrimitiveRequest, BooleanOperationRequest, AIGenerationRequest, TransformRequest, ExportRequest, ExportResponse
from pydantic import BaseModel
from typing import Dict, Optional
import trimesh
import numpy as np
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
        print("AI Generation Result:", result)
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





@router.post("/object-studio/refine", response_model=MeshRemediationResponse)
async def remediate_mesh(request: MeshRemediationRequest):
    """Apply mesh remediation operations with proper state updates"""
    try:
        if request.mesh_id not in meshes_store:
            raise HTTPException(status_code=404, detail="Mesh not found")
        
        mesh_data = meshes_store[request.mesh_id]
        original_mesh = reconstruct_mesh(mesh_data)
        
        # Store original counts for response
        original_vertex_count = len(original_mesh.vertices)
        original_face_count = len(original_mesh.faces)
        
        print(f"🔧 Applying {request.operation} on mesh {request.mesh_id}")
        print(f"📊 Original: {original_vertex_count} vertices, {original_face_count} faces")
        
        # Validate mesh before processing
        if original_face_count == 0:
            raise HTTPException(status_code=400, detail="Mesh has no faces")
        
        if original_face_count < 4:
            raise HTTPException(status_code=400, detail="Mesh has too few faces for processing")
        
        # Apply the requested operation
        result_mesh = original_mesh  # Start with original
        
        if request.operation == 'decimate':
            result_mesh = await apply_decimation(original_mesh, request.parameters)
        elif request.operation == 'smooth':
            result_mesh = await apply_smoothing(original_mesh, request.parameters)
        elif request.operation == 'remesh':
            result_mesh = await apply_remeshing(original_mesh, request.parameters)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {request.operation}")
        
        # CRITICAL: Check if the operation actually changed the mesh
        if (len(result_mesh.vertices) == original_vertex_count and 
            len(result_mesh.faces) == original_face_count):
            print("⚠️ Operation produced no changes to mesh geometry")
            # Try a more aggressive approach
            if request.operation == 'decimate':
                print("  ↳ Trying aggressive convex hull decimation")
                result_mesh = original_mesh.convex_hull
            elif request.operation == 'smooth':
                print("  ↳ Trying aggressive subdivision smoothing") 
                result_mesh = original_mesh.subdivide()
                result_mesh = result_mesh.subdivide()  # Double subdivision
            elif request.operation == 'remesh':
                print("  ↳ Trying voxel remeshing with smaller voxels")
                try:
                    bounds = original_mesh.bounds
                    diagonal = np.linalg.norm(bounds[1] - bounds[0])
                    voxel_size = diagonal / 15.0
                    voxel_grid = original_mesh.voxelized(pitch=voxel_size)
                    result_mesh = voxel_grid.as_boxes()
                except:
                    result_mesh = original_mesh.convex_hull
        
        # Validate result
        if len(result_mesh.faces) == 0:
            print("⚠️ Operation resulted in empty mesh, using original")
            result_mesh = original_mesh
        
        # Ensure mesh is valid
        try:
            result_mesh.fix_normals()
            #result_mesh.remove_duplicate_vertices()
        except Exception as cleanup_error:
            print(f"⚠️ Could not clean up result mesh: {cleanup_error}")
        
        # CRITICAL: Update the mesh in storage with the NEW mesh
        meshes_store[request.mesh_id]['mesh'] = result_mesh
        # Also update mesh_data for AI-generated meshes
        meshes_store[request.mesh_id]['mesh_data'] = {
            'vertices': result_mesh.vertices.tolist(),
            'faces': result_mesh.faces.tolist()
        }
        
        response_data = MeshRemediationResponse(
            mesh_id=request.mesh_id,
            vertices=result_mesh.vertices.tolist(),
            faces=result_mesh.faces.tolist(),
            operation=request.operation,
            original_vertex_count=original_vertex_count,
            new_vertex_count=len(result_mesh.vertices),
            original_face_count=original_face_count,
            new_face_count=len(result_mesh.faces)
        )
        
        reduction = ((original_face_count - len(result_mesh.faces)) / original_face_count * 100)
        print(f"✅ {request.operation} completed: {original_face_count} -> {len(result_mesh.faces)} faces ({reduction:+.1f}% change)")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Remediation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Remediation failed: {str(e)}")
    

# Helper function to reconstruct mesh from stored data
def reconstruct_mesh(mesh_data: Dict) -> trimesh.Trimesh:
    """Reconstruct trimesh object from stored data"""
    try:
        if 'mesh' in mesh_data and mesh_data['mesh'] is not None:
            return mesh_data['mesh']
        elif 'mesh_data' in mesh_data:
            vertices = np.array(mesh_data['mesh_data']['vertices'])
            faces = np.array(mesh_data['mesh_data']['faces'])
            return trimesh.Trimesh(vertices=vertices, faces=faces)
        else:
            raise ValueError("No mesh data found")
    except Exception as e:
        raise ValueError(f"Failed to reconstruct mesh: {str(e)}")

# Replace your mesh operation implementations with these:
# Replace your mesh operation implementations with these:

async def apply_decimation(mesh: trimesh.Trimesh, parameters: Dict) -> trimesh.Trimesh:
    """Apply mesh decimation that actually modifies the mesh"""
    try:
        target_ratio = parameters.get('value', 50) / 100.0
        target_face_count = int(len(mesh.faces) * target_ratio)
        
        # Ensure we don't decimate below a minimum face count
        min_faces = max(10, int(len(mesh.faces) * 0.1))
        target_face_count = max(min_faces, target_face_count)
        
        print(f"🔧 Decimating mesh: {len(mesh.faces)} -> {target_face_count} faces")
        
        # METHOD 1: For significant reduction, use convex hull approach
        if target_ratio < 0.7:  # Use convex hull for >30% reduction
            print("  ↳ Using convex hull method")
            result_mesh = mesh.convex_hull
            
            # If convex hull has too few faces, add some back with subdivision
            current_faces = len(result_mesh.faces)
            subdivision_count = 0
            while current_faces < target_face_count and subdivision_count < 3:
                result_mesh = result_mesh.subdivide()
                current_faces = len(result_mesh.faces)
                subdivision_count += 1
                print(f"    Subdivision {subdivision_count}: {current_faces} faces")
            
        else:
            # METHOD 2: For moderate reduction, use voxel-based approach
            print("  ↳ Using voxel method")
            try:
                bounds = mesh.bounds
                diagonal = np.linalg.norm(bounds[1] - bounds[0])
                voxel_size = diagonal / 8.0  # More aggressive voxel size
                
                voxel_grid = mesh.voxelized(pitch=voxel_size)
                if len(voxel_grid.faces) > 0:
                    result_mesh = voxel_grid.as_boxes()
                    print(f"    Voxel result: {len(result_mesh.faces)} faces")
                else:
                    print("    Voxel failed, using convex hull")
                    result_mesh = mesh.convex_hull
            except Exception as voxel_error:
                print(f"    Voxel error: {voxel_error}")
                result_mesh = mesh.convex_hull
        
        # Final check - if we ended up with more faces than target, use the original
        if len(result_mesh.faces) > len(mesh.faces):
            print("  ↳ Result has more faces than original, using moderate convex hull")
            result_mesh = mesh.convex_hull
        
        print(f"✅ Decimation completed: {len(mesh.faces)} -> {len(result_mesh.faces)} faces")
        return result_mesh
        
    except Exception as e:
        print(f"❌ Decimation failed: {str(e)}")
        return mesh

async def apply_smoothing(mesh: trimesh.Trimesh, parameters: Dict) -> trimesh.Trimesh:
    """Apply mesh smoothing that actually modifies the mesh"""
    try:
        iterations = parameters.get('value', 3)
        
        print(f"🔧 Smoothing mesh with {iterations} iterations")
        
        # Start with a fresh copy to ensure we modify it
        smoothed_mesh = mesh.copy()
        
        print(f"  ↳ Starting face count: {len(smoothed_mesh.faces)}")
        
        # Apply subdivision for smoothing
        for i in range(iterations):
            try:
                # Store current face count before subdivision
                before_faces = len(smoothed_mesh.faces)
                
                # Apply subdivision
                subdivided = smoothed_mesh.subdivide()
                
                # Check if subdivision actually worked
                if len(subdivided.faces) > before_faces and len(subdivided.faces) > 0:
                    smoothed_mesh = subdivided
                    print(f"  ↳ Subdivision {i+1}: {before_faces} -> {len(smoothed_mesh.faces)} faces")
                else:
                    print(f"  ↳ Subdivision {i+1} produced no change or invalid mesh")
                    break
                    
            except Exception as subdiv_error:
                print(f"  ↳ Subdivision {i+1} failed: {subdiv_error}")
                break
        
        # If smoothing didn't change anything, use a different approach
        if len(smoothed_mesh.faces) == len(mesh.faces):
            print("  ↳ Subdivision had no effect, trying convex hull for smoothing")
            try:
                # Sometimes convex hull can create a smoother version
                smoothed_mesh = mesh.convex_hull
                # Add one subdivision to smooth the convex hull
                smoothed_mesh = smoothed_mesh.subdivide()
            except:
                smoothed_mesh = mesh
        
        print(f"✅ Smoothing completed: {len(mesh.faces)} -> {len(smoothed_mesh.faces)} faces")
        return smoothed_mesh
        
    except Exception as e:
        print(f"❌ Smoothing failed: {str(e)}")
        return mesh

async def apply_remeshing(mesh: trimesh.Trimesh, parameters: Dict) -> trimesh.Trimesh:
    """Apply remeshing that actually creates a new mesh"""
    try:
        print(f"🔧 Remeshing mesh with {len(mesh.faces)} faces")
        
        # METHOD 1: Try voxel-based remeshing first
        try:
            bounds = mesh.bounds
            diagonal = np.linalg.norm(bounds[1] - bounds[0])
            voxel_size = diagonal / 10.0  # Balanced detail level
            
            print(f"  ↳ Using voxel size: {voxel_size:.4f}")
            
            voxel_grid = mesh.voxelized(pitch=voxel_size)
            
            if hasattr(voxel_grid, 'as_boxes') and len(voxel_grid.faces) > 0:
                remeshed = voxel_grid.as_boxes()
                print(f"  ↳ Voxel remeshing successful: {len(remeshed.faces)} faces")
                
                # Clean up the result
                if len(remeshed.faces) > 0:
                    try:
                        # remeshed.remove_duplicate_vertices()
                        remeshed.fix_normals()
                    except:
                        pass
                    return remeshed
                    
        except Exception as voxel_error:
            print(f"  ↳ Voxel remeshing failed: {voxel_error}")
        
        # METHOD 2: Use convex hull with progressive subdivision
        print("  ↳ Using convex hull + progressive subdivision")
        remeshed = mesh.convex_hull
        
        # Target face count - aim for similar complexity but cleaner topology
        target_faces = max(len(mesh.faces) // 2, 50, len(remeshed.faces))
        
        print(f"  ↳ Target face count: {target_faces}")
        
        # Apply controlled subdivision
        max_subdivisions = 3
        for i in range(max_subdivisions):
            if len(remeshed.faces) < target_faces:
                try:
                    before_faces = len(remeshed.faces)
                    remeshed = remeshed.subdivide()
                    after_faces = len(remeshed.faces)
                    print(f"    Subdivision {i+1}: {before_faces} -> {after_faces} faces")
                    
                    if after_faces <= before_faces:  # No change, stop
                        break
                except:
                    break
            else:
                break
        
        # Final cleanup
        try:
            #remeshed.remove_duplicate_vertices()
            remeshed.fix_normals()
        except:
            print("  ↳ Could not clean up remeshed mesh")
        
        print(f"✅ Remeshing completed: {len(mesh.faces)} -> {len(remeshed.faces)} faces")
        return remeshed
        
    except Exception as e:
        print(f"❌ Remeshing failed: {str(e)}")
        return mesh
    

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
