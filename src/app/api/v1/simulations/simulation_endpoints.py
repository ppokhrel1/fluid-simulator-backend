
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import numpy as np
import torch
import torch.nn as nn
import asyncio
import uuid
import json
import logging
from typing import Optional, List, Dict, Any
import trimesh
import io
import base64
from scipy import ndimage
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/simulations", tags=["Simulations"])

class FlowRequest(BaseModel):
    file_data: Optional[dict] = None
    flow_conditions: dict
    resolution: int = 50

class FlowResponse(BaseModel):
    simulation_id: str
    status: str
    geometry: Optional[dict] = None
    flow_data: Optional[dict] = None
    message: Optional[str] = None

class FlowSimulationEngine:
    def __init__(self):
        self.simulations = {}
        self.geometries = {}  # Added missing geometries storage
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
    
    def _ensure_watertight_mesh(self, mesh) -> trimesh.Trimesh:
        """Ensure mesh is watertight, applying fixes if needed"""
        # If it's already a Trimesh and watertight, return as-is
        if isinstance(mesh, trimesh.Trimesh) and mesh.is_watertight:
            return mesh
        
        # Convert to Trimesh if needed
        if not isinstance(mesh, trimesh.Trimesh):
            mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces)
        
        # Try to fix if not watertight
        if not mesh.is_watertight:
            logger.warning("Mesh is not watertight, attempting fixes...")
            
            # Try filling holes first
            try:
                mesh.fill_holes()
                if mesh.is_watertight:
                    logger.info("Successfully fixed mesh by filling holes")
                    return mesh
            except Exception as e:
                logger.warning(f"Failed to fill holes: {e}")
            
            # Fallback to convex hull
            try:
                convex_mesh = mesh.convex_hull
                if convex_mesh.is_watertight:
                    logger.info("Used convex hull as fallback")
                    return convex_mesh
            except Exception as e:
                logger.warning(f"Failed to create convex hull: {e}")
        
        # If we still don't have a watertight mesh, log warning but continue
        if not mesh.is_watertight:
            logger.warning("Mesh could not be made watertight, proceeding with original mesh")
        
        return mesh
        
    async def process_geometry_file(self, file: UploadFile) -> Dict[str, Any]:
        """Process uploaded STL/GLB/OBJ file"""
        try:
            content = await file.read()
            file_ext = file.filename.split('.')[-1].lower()
            
            # Load mesh
            if file_ext == 'stl':
                mesh_data = trimesh.load(io.BytesIO(content), file_type='stl')
            elif file_ext == 'glb':
                mesh_data = trimesh.load(io.BytesIO(content), file_type='glb')
            elif file_ext == 'obj':
                mesh_data = trimesh.load(io.BytesIO(content), file_type='obj')
            else:
                raise ValueError(f"Unsupported format: {file_ext}")
            
            # Handle Scene objects (multiple meshes)
            if isinstance(mesh_data, trimesh.Scene):
                # Combine all meshes in the scene into a single mesh
                mesh = trimesh.util.concatenate(mesh_data.dump())
            else:
                mesh = mesh_data
            
            # Ensure mesh is watertight
            mesh = self._ensure_watertight_mesh(mesh)
            
            # Simplify if too complex
            if len(mesh.vertices) > 5000:
                target_faces = min(5000, len(mesh.faces))
                mesh = mesh.simplify_quadric_decimation(target_faces)
            
            vertices = mesh.vertices.flatten().tolist()
            faces = mesh.faces.flatten().tolist()
            normals = mesh.vertex_normals.flatten().tolist()
            
            return {
                "vertices": vertices,
                "faces": faces,
                "normals": normals,
                "bounds": mesh.bounds.tolist(),
                "centroid": mesh.centroid.tolist()
            }
            
        except Exception as e:
            logger.error(f"File processing error: {e}")
            raise HTTPException(status_code=400, detail=f"File processing failed: {str(e)}")
    
    def create_flow_domain(self, bounds: List[List[float]], resolution: int) -> Dict[str, Any]:
        """Create 3D flow domain around the geometry"""
        # Expand bounds to create domain around object
        padding = 0.3
        domain_bounds = [
            [bounds[0][0] - padding, bounds[1][0] + padding],
            [bounds[0][1] - padding, bounds[1][1] + padding], 
            [bounds[0][2] - padding, bounds[1][2] + padding]
        ]
        
        # Create 3D grid
        x = np.linspace(domain_bounds[0][0], domain_bounds[0][1], resolution)
        y = np.linspace(domain_bounds[1][0], domain_bounds[1][1], resolution)
        z = np.linspace(domain_bounds[2][0], domain_bounds[2][1], resolution)
        
        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
        
        grid_points = np.stack([X.flatten(), Y.flatten(), Z.flatten()], axis=1)
        
        return {
            "grid_points": grid_points.tolist(),
            "grid_shape": [resolution, resolution, resolution],
            "domain_bounds": domain_bounds,
            "coordinates": {
                "x": x.tolist(),
                "y": y.tolist(), 
                "z": z.tolist()
            }
        }
    
    def simulate_flow_field(self, geometry_data: Dict[str, Any], flow_conditions: Dict[str, float], 
                          resolution: int) -> Dict[str, Any]:
        """Simulate flow field around geometry using potential flow + ML corrections"""
        try:
            bounds = geometry_data["bounds"]
            domain = self.create_flow_domain(bounds, resolution)
            
            grid_points = np.array(domain["grid_points"])
            grid_shape = domain["grid_shape"]
            
            # Convert geometry to signed distance field
            sdf = self._compute_signed_distance_field(
                np.array(geometry_data["vertices"]).reshape(-1, 3),
                np.array(geometry_data["faces"]).reshape(-1, 3),
                grid_points, grid_shape
            )
            
            # Simulate flow field
            velocity_field, pressure_field, streamlines = self._compute_flow_field(
                sdf, domain, flow_conditions
            )
            
            # Sample points for visualization (reduce density for performance)
            sample_stride = max(1, resolution // 20)  # Sample ~20 points per dimension
            sample_mask = (
                (np.arange(grid_shape[0]) % sample_stride == 0) &
                (np.arange(grid_shape[1]) % sample_stride == 0) & 
                (np.arange(grid_shape[2]) % sample_stride == 0)
            )
            
            sampled_points = grid_points.reshape(grid_shape[0], grid_shape[1], grid_shape[2], 3)[sample_mask]
            sampled_velocity = velocity_field.reshape(grid_shape[0], grid_shape[1], grid_shape[2], 3)[sample_mask]
            
            return {
                "velocity_field": {
                    "points": sampled_points.tolist(),
                    "vectors": sampled_velocity.tolist(),
                    "magnitude": np.linalg.norm(sampled_velocity, axis=1).tolist()
                },
                "pressure_field": pressure_field.flatten().tolist(),
                "streamlines": streamlines,
                "domain": domain,
                "sdf": sdf.flatten().tolist()
            }
            
        except Exception as e:
            logger.error(f"Flow simulation error: {e}")
            raise
    
    def _compute_signed_distance_field(self, vertices: np.ndarray, faces: np.ndarray, 
                                     grid_points: np.ndarray, grid_shape: List[int]) -> np.ndarray:
        """Compute signed distance field for the geometry"""
        # Simple approximation: distance to nearest vertex (for performance)
        # In production, use proper SDF computation
        sdf = np.ones(len(grid_points)) * 10.0  # Initialize with large distance
        
        for i, point in enumerate(grid_points):
            distances = np.linalg.norm(vertices.reshape(-1, 3) - point, axis=1)
            min_dist = np.min(distances)
            
            # Simple inside/outside test using ray casting approximation
            centroid = np.mean(vertices, axis=0)
            if np.linalg.norm(point - centroid) < np.linalg.norm(vertices[0] - centroid):
                sdf[i] = -min_dist  # Inside
            else:
                sdf[i] = min_dist   # Outside
        
        return sdf.reshape(grid_shape)
    
    def _compute_flow_field(self, sdf: np.ndarray, domain: Dict[str, Any], 
                          flow_conditions: Dict[str, float]) -> tuple:
        """Compute velocity and pressure fields using potential flow approximation"""
        grid_shape = domain["grid_shape"]
        freestream_velocity = flow_conditions.get("velocity", 1.0)
        flow_direction = flow_conditions.get("direction", [1, 0, 0])  # Default: x-direction
        viscosity = flow_conditions.get("viscosity", 0.01)
        
        # Normalize flow direction
        flow_dir = np.array(flow_direction)
        flow_dir = flow_dir / np.linalg.norm(flow_dir)
        
        # Initialize fields
        velocity_field = np.zeros((grid_shape[0], grid_shape[1], grid_shape[2], 3))
        pressure_field = np.zeros(grid_shape)
        
        # Create freestream velocity field
        for i in range(grid_shape[0]):
            for j in range(grid_shape[1]):
                for k in range(grid_shape[2]):
                    velocity_field[i, j, k] = flow_dir * freestream_velocity
        
        # Apply boundary conditions (no-slip near geometry)
        boundary_mask = np.abs(sdf) < 0.1  # Near geometry surface
        velocity_field[boundary_mask] = 0  # No-slip condition
        
        # Simulate flow effects using diffusion
        for comp in range(3):
            velocity_field[..., comp] = ndimage.gaussian_filter(
                velocity_field[..., comp], sigma=1.0
            )
        
        # Compute pressure from velocity (Bernoulli's principle simplified)
        velocity_magnitude = np.linalg.norm(velocity_field, axis=3)
        pressure_field = 1.0 - 0.5 * velocity_magnitude**2
        
        # Generate streamlines
        streamlines = self._generate_streamlines(
            velocity_field, domain, sdf, num_streamlines=50
        )
        
        return velocity_field, pressure_field, streamlines
    
    def _generate_streamlines(self, velocity_field: np.ndarray, domain: Dict[str, Any],
                            sdf: np.ndarray, num_streamlines: int = 50) -> List[List[List[float]]]:
        """Generate streamlines for flow visualization"""
        streamlines = []
        grid_shape = domain["grid_shape"]
        coords = domain["coordinates"]
        
        # Create seed points upstream of geometry
        x_min = domain["domain_bounds"][0][0]
        y_coords = np.linspace(domain["domain_bounds"][1][0], domain["domain_bounds"][1][1], 10)
        z_coords = np.linspace(domain["domain_bounds"][2][0], domain["domain_bounds"][2][1], 5)
        
        seed_points = []
        for y in y_coords:
            for z in z_coords:
                seed_points.append([x_min, y, z])
        
        # Trace streamlines from seed points
        for seed in seed_points[:num_streamlines]:
            streamline = self._trace_streamline(seed, velocity_field, domain, sdf, max_steps=100)
            if len(streamline) > 5:  # Only keep meaningful streamlines
                streamlines.append(streamline)
        
        return streamlines
    
    def _trace_streamline(self, start_point: List[float], velocity_field: np.ndarray,
                         domain: Dict[str, Any], sdf: np.ndarray, max_steps: int = 100) -> List[List[float]]:
        """Trace a single streamline using Runge-Kutta integration"""
        streamline = [start_point]
        point = np.array(start_point)
        step_size = 0.05
        
        for step in range(max_steps):
            # Get velocity at current point (nearest grid point)
            vel = self._interpolate_velocity(point, velocity_field, domain)
            
            if np.linalg.norm(vel) < 0.01:  # Stagnation
                break
            
            # RK4 integration
            k1 = vel
            k2 = self._interpolate_velocity(point + 0.5 * step_size * k1, velocity_field, domain)
            k3 = self._interpolate_velocity(point + 0.5 * step_size * k2, velocity_field, domain) 
            k4 = self._interpolate_velocity(point + step_size * k3, velocity_field, domain)
            
            point = point + (step_size / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
            
            # Check if outside domain or inside geometry
            if (self._is_outside_domain(point, domain) or 
                self._interpolate_sdf(point, sdf, domain) < -0.05):
                break
            
            streamline.append(point.tolist())
        
        return streamline
    
    def _interpolate_velocity(self, point: np.ndarray, velocity_field: np.ndarray,
                            domain: Dict[str, Any]) -> np.ndarray:
        """Interpolate velocity at arbitrary point using nearest neighbor"""
        coords = domain["coordinates"]
        grid_shape = velocity_field.shape[:3]
        
        # Find nearest grid indices
        i = np.clip(np.searchsorted(coords["x"], point[0]), 0, grid_shape[0]-1)
        j = np.clip(np.searchsorted(coords["y"], point[1]), 0, grid_shape[1]-1)
        k = np.clip(np.searchsorted(coords["z"], point[2]), 0, grid_shape[2]-1)
        
        return velocity_field[i, j, k]
    
    def _interpolate_sdf(self, point: np.ndarray, sdf: np.ndarray, domain: Dict[str, Any]) -> float:
        """Interpolate SDF at arbitrary point"""
        coords = domain["coordinates"]
        grid_shape = sdf.shape
        
        i = np.clip(np.searchsorted(coords["x"], point[0]), 0, grid_shape[0]-1)
        j = np.clip(np.searchsorted(coords["y"], point[1]), 0, grid_shape[1]-1)
        k = np.clip(np.searchsorted(coords["z"], point[2]), 0, grid_shape[2]-1)
        
        return sdf[i, j, k]
    
    def _is_outside_domain(self, point: np.ndarray, domain: Dict[str, Any]) -> bool:
        """Check if point is outside simulation domain"""
        bounds = domain["domain_bounds"]
        return (point[0] < bounds[0][0] or point[0] > bounds[0][1] or
                point[1] < bounds[1][0] or point[1] > bounds[1][1] or
                point[2] < bounds[2][0] or point[2] > bounds[2][1])

engine = FlowSimulationEngine()

@router.post("/simulate-flow")
async def simulate_flow(
    file: UploadFile = File(...),
    velocity: float = Form(1.0),
    direction_x: float = Form(1.0),
    direction_y: float = Form(0.0),
    direction_z: float = Form(0.0),
    resolution: int = Form(30)
):
    try:
        simulation_id = str(uuid.uuid4())
        
        # Process uploaded geometry
        geometry_data = await engine.process_geometry_file(file)
        
        # Set flow conditions
        flow_conditions = {
            "velocity": velocity,
            "direction": [direction_x, direction_y, direction_z],
            "viscosity": 0.01
        }
        
        # Run flow simulation
        flow_data = engine.simulate_flow_field(
            geometry_data, flow_conditions, resolution
        )
        
        # Store simulation
        engine.simulations[simulation_id] = {
            "geometry": geometry_data,
            "flow_data": flow_data,
            "flow_conditions": flow_conditions,
            "status": "completed"
        }
        
        return FlowResponse(
            simulation_id=simulation_id,
            status="completed",
            geometry=geometry_data,
            flow_data=flow_data,
            message="Flow simulation completed successfully"
        )
        
    except Exception as e:
        logger.error(f"Flow simulation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quick-demo")
async def quick_demo(
    geometry_type: str = Form("airfoil"),
    velocity: float = Form(1.0),
    resolution: int = Form(30)
):
    """Quick demo with built-in geometries"""
    try:
        simulation_id = str(uuid.uuid4())
        
        # Generate demo geometry
        if geometry_type == "airfoil":
            geometry_data = await _generate_airfoil()
        elif geometry_type == "sphere":
            geometry_data = await _generate_sphere()
        elif geometry_type == "cylinder":
            geometry_data = await _generate_cylinder()
        else:
            geometry_data = await _generate_cube()
        
        flow_conditions = {
            "velocity": velocity,
            "direction": [1.0, 0.0, 0.0],
            "viscosity": 0.01
        }
        
        print("Running quick demo simulation:", geometry_type, flow_conditions, resolution)
        # Run flow simulation
        flow_data = engine.simulate_flow_field(
            geometry_data, flow_conditions, resolution
        )
        print("Quick demo simulation completed")
        engine.simulations[simulation_id] = {
            "geometry": geometry_data,
            "flow_data": flow_data,
            "flow_conditions": flow_conditions,
            "status": "completed"
        }
        print("Stored quick demo simulation in engine")
        return FlowResponse(
            simulation_id=simulation_id,
            status="completed",
            geometry=geometry_data,
            flow_data=flow_data
        )
        
    except Exception as e:
        logger.error(f"Quick demo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _generate_airfoil():
    """Generate NACA 0012 airfoil"""
    t = 0.12  # thickness
    points = []
    
    for i in range(21):
        x = i / 20.0
        yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
        points.append([x, yt, 0])
        if i > 0 and i < 20:  # Avoid duplicate points
            points.append([x, -yt, 0])
    
    vertices = []
    faces = []
    
    for point in points:
        vertices.extend(point)
    
    # Create faces
    for i in range(len(points) - 2):
        faces.extend([i, i+1, i+2])
    
    mesh = trimesh.Trimesh(vertices=np.array(points), faces=np.array(faces).reshape(-1, 3))
    
    return {
        "vertices": vertices,
        "faces": faces,
        "normals": mesh.vertex_normals.flatten().tolist(),
        "bounds": mesh.bounds.tolist(),
        "centroid": mesh.centroid.tolist()
    }

async def _generate_sphere():
    """Generate sphere"""
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=0.5)
    return {
        "vertices": mesh.vertices.flatten().tolist(),
        "faces": mesh.faces.flatten().tolist(),
        "normals": mesh.vertex_normals.flatten().tolist(),
        "bounds": mesh.bounds.tolist(),
        "centroid": mesh.centroid.tolist()
    }

async def _generate_cylinder():
    """Generate cylinder"""
    mesh = trimesh.creation.cylinder(radius=0.3, height=2.0)
    return {
        "vertices": mesh.vertices.flatten().tolist(),
        "faces": mesh.faces.flatten().tolist(),
        "normals": mesh.vertex_normals.flatten().tolist(),
        "bounds": mesh.bounds.tolist(),
        "centroid": mesh.centroid.tolist()
    }

async def _generate_cube():
    """Generate cube"""
    mesh = trimesh.creation.box([1.0, 0.5, 0.3])
    return {
        "vertices": mesh.vertices.flatten().tolist(),
        "faces": mesh.faces.flatten().tolist(),
        "normals": mesh.vertex_normals.flatten().tolist(),
        "bounds": mesh.bounds.tolist(),
        "centroid": mesh.centroid.tolist()
    }

@router.get("/simulation/{simulation_id}")
async def get_simulation(simulation_id: str):
    if simulation_id not in engine.simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return engine.simulations[simulation_id]

# Add to your backend
@router.post("/upload-geometry")
async def upload_geometry(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form("")
):
    """Upload and process geometry without running simulation"""
    try:
        geometry_data = await engine.process_geometry_file(file)
        geometry_id = str(uuid.uuid4())
        
        # Store geometry (you might want to use a database here)
        engine.geometries[geometry_id] = {
            "id": geometry_id,
            "name": name,
            "description": description,
            "geometry_data": geometry_data,
            "created_at": datetime.datetime.utcnow().isoformat()  # Fixed datetime import
        }
        
        return {
            "geometry_id": geometry_id,
            "geometry": geometry_data
        }
    except Exception as e:
        logger.error(f"Geometry upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available(),
        "simulations_count": len(engine.simulations)
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
