# backend/app/api/endpoints/simulations.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import uuid
import json
from datetime import datetime
import numpy as np
import trimesh
import asyncio

from src.app.api.services.simulation_service import simulation_service as engine

from ...services.simulation_service import simulation_service, SimulationPlatform

router = APIRouter(prefix="/simulations", tags=["simulations"])

@router.post("/create", response_model=Dict[str, Any])
async def create_simulation(
    name: str = Form(...),
    geometry_data: str = Form(...),  # JSON string of geometry data
    physics_config: str = Form(...),  # JSON string of physics configuration
    platform: str = Form("pinn")
):
    """Create a new simulation"""
    try:
        # Parse JSON data
        geometry_dict = json.loads(geometry_data)
        physics_dict = json.loads(physics_config)
        
        simulation_data = {
            "name": name,
            "geometry": geometry_dict,
            "physics_config": physics_dict,
            "platform": platform
        }
        
        simulation = await simulation_service.create_simulation(simulation_data)
        return simulation
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create simulation: {str(e)}")

@router.get("/{simulation_id}", response_model=Dict[str, Any])
async def get_simulation(simulation_id: str):
    """Get simulation by ID"""
    simulation = simulation_service.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation

@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_simulations():
    """Get all simulations"""
    return simulation_service.get_all_simulations()

@router.delete("/{simulation_id}")
async def delete_simulation(simulation_id: str):
    """Delete simulation by ID"""
    success = simulation_service.delete_simulation(simulation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"message": "Simulation deleted successfully"}

@router.get("/platforms/status")
async def get_platform_status():
    """Get status of all simulation platforms"""
    return simulation_service.get_platform_status()

@router.post("/fluid-flow")
async def simulate_fluid_flow(
    file: UploadFile = File(...),
    velocity: float = Form(1.0),
    direction_x: float = Form(1.0),
    direction_y: float = Form(0.0),
    direction_z: float = Form(0.0),
    viscosity: float = Form(0.01),
    resolution: int = Form(50)
):
    """Specialized endpoint for fluid flow simulation using PINN"""
    try:
        # Process uploaded geometry
        geometry_data = await engine.process_geometry_file(file)
        
        # Create physics configuration for fluid flow
        physics_config = {
            "type": "fluid",
            "flow_velocity": velocity,
            "flow_direction": [direction_x, direction_y, direction_z],
            "viscosity": viscosity,
            "resolution": resolution
        }
        
        simulation_data = {
            "name": f"Fluid_Flow_{uuid.uuid4().hex[:8]}",
            "geometry": geometry_data,
            "physics_config": physics_config,
            "platform": "pinn"
        }
        
        # Create and run simulation
        simulation = await simulation_service.create_simulation(simulation_data)
        
        # Wait for simulation to complete
        max_wait_time = 300  # 5 minutes timeout
        wait_interval = 1  # Check every second
        
        for _ in range(max_wait_time):
            current_sim = simulation_service.get_simulation(simulation["id"])
            if current_sim["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(wait_interval)
        
        # Get final simulation result
        final_simulation = simulation_service.get_simulation(simulation["id"])
        
        if final_simulation["status"] == "failed":
            raise HTTPException(status_code=500, detail=final_simulation.get("error", "Simulation failed"))
        
        return {
            "simulation_id": simulation["id"],
            "status": "completed",
            "geometry": geometry_data,
            "flow_data": final_simulation["results"].get("flow_data", {}),
            "simulation_metrics": final_simulation["results"].get("simulation_metrics", {}),
            "message": "Fluid flow simulation completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fluid flow simulation error: {str(e)}")

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

@router.post("/quick-demo")
async def quick_demo(
    geometry_type: str = Form("sphere"),
    velocity: float = Form(1.0),
    viscosity: float = Form(0.01),
    resolution: int = Form(30)
):
    """Quick demo with built-in geometries using PINN"""
    try:
        # Generate demo geometry
        if geometry_type == "airfoil":
            geometry_data = await _generate_airfoil()
        elif geometry_type == "cylinder":
            geometry_data = await _generate_cylinder()
        elif geometry_type == "cube":
            geometry_data = await _generate_cube()
        else:
            geometry_data = await _generate_sphere()  # Default to sphere
        
        # Create physics configuration
        physics_config = {
            "type": "fluid",
            "flow_velocity": velocity,
            "flow_direction": [1.0, 0.0, 0.0],
            "viscosity": viscosity,
            "resolution": resolution
        }
        
        simulation_data = {
            "name": f"Demo_{geometry_type}_{uuid.uuid4().hex[:8]}",
            "geometry": geometry_data,
            "physics_config": physics_config,
            "platform": "pinn"
        }
        
        # Create and run simulation
        simulation = await simulation_service.create_simulation(simulation_data)
        
        # Wait for simulation to complete (same as fluid-flow endpoint)
        max_wait_time = 300
        wait_interval = 1
        
        for _ in range(max_wait_time):
            current_sim = simulation_service.get_simulation(simulation["id"])
            if current_sim["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(wait_interval)
        
        # Get final simulation result
        final_simulation = simulation_service.get_simulation(simulation["id"])
        
        if final_simulation["status"] == "failed":
            raise HTTPException(status_code=500, detail=final_simulation.get("error", "Simulation failed"))
        print(final_simulation["results"].get("simulation_metrics", {}))

        return {
            "simulation_id": simulation["id"],
            "status": "completed",
            "geometry": geometry_data,
            "flow_data": final_simulation["results"].get("flow_data", {}),
            "simulation_metrics": final_simulation["results"].get("simulation_metrics", {}),
            "message": f"Demo simulation for {geometry_type} completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick demo error: {str(e)}")

# Alternative async quick-demo that returns immediately and processes in background
@router.post("/quick-demo-async")
async def quick_demo_async(
    background_tasks: BackgroundTasks,
    geometry_type: str = Form("sphere"),
    velocity: float = Form(1.0),
    viscosity: float = Form(0.01),
    resolution: int = Form(30)
):
    """Quick demo that returns immediately and processes in background"""
    try:
        simulation_id = str(uuid.uuid4())
        
        # Generate demo geometry
        if geometry_type == "airfoil":
            geometry_data = await _generate_airfoil()
        elif geometry_type == "cylinder":
            geometry_data = await _generate_cylinder()
        elif geometry_type == "cube":
            geometry_data = await _generate_cube()
        else:
            geometry_data = await _generate_sphere()
        
        # Store initial simulation data
        initial_simulation = {
            "id": simulation_id,
            "name": f"Demo_{geometry_type}_{simulation_id[:8]}",
            "geometry": geometry_data,
            "physics_config": {
                "type": "fluid",
                "flow_velocity": velocity,
                "flow_direction": [1.0, 0.0, 0.0],
                "viscosity": viscosity,
                "resolution": resolution
            },
            "platform": "pinn",
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "results": None,
            "error": None
        }
        
        simulation_service.active_simulations[simulation_id] = initial_simulation
        
        # Run simulation in background
        background_tasks.add_task(
            run_demo_simulation, 
            simulation_id, 
            geometry_data, 
            geometry_type, 
            velocity, 
            viscosity, 
            resolution
        )
        
        return {
            "simulation_id": simulation_id,
            "status": "running",
            "geometry": geometry_data,
            "message": f"Demo simulation for {geometry_type} started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick demo error: {str(e)}")

async def run_demo_simulation(simulation_id: str, geometry_data: dict, geometry_type: str, 
                            velocity: float, viscosity: float, resolution: int):
    """Run demo simulation in background"""
    try:
        # Update simulation status
        simulation_service.active_simulations[simulation_id]["status"] = "running"
        simulation_service.active_simulations[simulation_id]["started_at"] = datetime.utcnow().isoformat()
        
        # Create physics configuration
        physics_config = {
            "type": "fluid",
            "flow_velocity": velocity,
            "flow_direction": [1.0, 0.0, 0.0],
            "viscosity": viscosity,
            "resolution": resolution
        }
        
        simulation_data = {
            "name": f"Demo_{geometry_type}_{simulation_id[:8]}",
            "geometry": geometry_data,
            "physics_config": physics_config,
            "platform": "pinn"
        }
        
        # Run simulation
        results = await simulation_service._run_pinn_simulation(simulation_data)
        
        # Update simulation with results
        simulation_service.active_simulations[simulation_id].update({
            "status": "completed",
            "results": results,
            "completed_at": datetime.utcnow().isoformat(),
            "progress": 100
        })
        
    except Exception as e:
        simulation_service.active_simulations[simulation_id].update({
            "status": "failed",
            "error": str(e),
            "progress": 0
        })

@router.get("/simulation/{simulation_id}/status")
async def get_simulation_status(simulation_id: str):
    """Get simulation status and results"""
    simulation = simulation_service.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {
        "simulation_id": simulation_id,
        "status": simulation["status"],
        "progress": simulation.get("progress", 0),
        "geometry": simulation.get("geometry"),
        "flow_data": simulation.get("results", {}).get("flow_data") if simulation["status"] == "completed" else None,
        "error": simulation.get("error")
    }