# app/services/composition_engine.py
import trimesh
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class CompositionEngine:
    def __init__(self):
        self.supported_primitives = ['cube', 'sphere', 'cylinder', 'cone', 'torus']
    
    def create_primitive(self, shape_type: str, parameters: Dict) -> trimesh.Trimesh:
        """Create a primitive shape"""
        try:
            if shape_type == 'cube':
                size = parameters.get('size', 1.0)
                mesh = trimesh.creation.box([size, size, size])
                
            elif shape_type == 'sphere':
                radius = parameters.get('radius', 0.5)
                subdivisions = parameters.get('subdivisions', 2)
                mesh = trimesh.creation.icosphere(radius=radius, subdivisions=subdivisions)
                
            elif shape_type == 'cylinder':
                radius = parameters.get('radius', 0.5)
                height = parameters.get('height', 1.0)
                mesh = trimesh.creation.cylinder(radius=radius, height=height)
                
            elif shape_type == 'cone':
                radius = parameters.get('radius', 0.5)
                height = parameters.get('height', 1.0)
                mesh = trimesh.creation.cone(radius=radius, height=height)
                
            elif shape_type == 'torus':
                major_radius = parameters.get('major_radius', 1.0)
                minor_radius = parameters.get('minor_radius', 0.3)
                mesh = trimesh.creation.torus(major_radius=major_radius, minor_radius=minor_radius)
                
            else:
                raise ValueError(f"Unsupported primitive type: {shape_type}")
            
            # Ensure the mesh is valid
            if not mesh.is_watertight:
                mesh = mesh.convex_hull
                
            return mesh
            
        except Exception as e:
            logger.error(f"Error creating primitive {shape_type}: {str(e)}")
            raise
    
    def boolean_operation(self, mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh, operation: str) -> trimesh.Trimesh:
        """Perform boolean operations between two meshes"""
        try:
            # Ensure meshes are watertight for boolean operations
            if not mesh_a.is_watertight:
                mesh_a = mesh_a.convex_hull
            if not mesh_b.is_watertight:
                mesh_b = mesh_b.convex_hull
            
            if operation == 'union':
                result = mesh_a.union(mesh_b)
            elif operation == 'difference':
                result = mesh_a.difference(mesh_b)
            elif operation == 'intersection':
                result = mesh_a.intersection(mesh_b)
            else:
                raise ValueError(f"Unsupported boolean operation: {operation}")
            
            # If boolean operation fails, fall back to convex hull
            if result.is_empty or len(result.faces) == 0:
                logger.warning("Boolean operation failed, using convex hull")
                combined = trimesh.util.concatenate([mesh_a, mesh_b])
                result = combined.convex_hull
            
            return result
            
        except Exception as e:
            logger.error(f"Boolean operation failed: {str(e)}")
            # Fallback: return the first mesh
            return mesh_a
    
    def mesh_to_dict(self, mesh: trimesh.Trimesh) -> Dict:
        """Convert trimesh object to serializable dict"""
        return {
            'vertices': mesh.vertices.tolist(),
            'faces': mesh.faces.tolist(),
            'vertex_count': len(mesh.vertices),
            'face_count': len(mesh.faces)
        }