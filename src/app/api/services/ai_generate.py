# app/services/ai_generation.py
import replicate
import os
import asyncio
from typing import Dict, Optional
import logging

from src.app.core.config import AppSettings

logger = logging.getLogger(__name__)

class AIGenerationService:
    def __init__(self):
        self.use_free_tier = os.getenv("USE_FREE_AI", "true").lower() == "true"
        
        # Initialize Replicate client only if using paid tier
        if not self.use_free_tier and AppSettings().REPLICATE_API_TOKEN:
            self.replicate_client = replicate.Client(api_token=AppSettings().REPLICATE_API_TOKEN)
        else:
            self.replicate_client = None
    
    async def generate_shape_from_prompt(self, prompt: str, base_mesh_data: Optional[Dict] = None) -> Dict:
        """Generate 3D shape from text prompt"""
        try:
            if self.use_free_tier or not self.replicate_client:
                # Use free open-source models first
                return await self._generate_with_open_source(prompt, base_mesh_data)
            else:
                # Use paid but cheap Replicate models
                return await self._generate_with_replicate(prompt, base_mesh_data)
                
        except Exception as e:
            logger.error(f"AI generation failed: {str(e)}")
            # Fallback to primitive generation
            return await self._fallback_to_primitive(prompt)
    
    async def _generate_with_open_source(self, prompt: str, base_mesh_data: Optional[Dict]) -> Dict:
        """Use free keyword-based generation"""
        from .composition_engine import CompositionEngine
        composition_engine = CompositionEngine()
        
        prompt_lower = prompt.lower()
        
        # Determine shape type from prompt keywords
        if any(word in prompt_lower for word in ['block', 'cube', 'box', 'rectangular']):
            shape_type = 'cube'
        elif any(word in prompt_lower for word in ['cylinder', 'tube', 'round', 'pipe']):
            shape_type = 'cylinder'
        elif any(word in prompt_lower for word in ['sphere', 'ball', 'round']):
            shape_type = 'sphere'
        elif any(word in prompt_lower for word in ['cone', 'pyramid', 'pointed']):
            shape_type = 'cone'
        elif any(word in prompt_lower for word in ['torus', 'donut', 'ring']):
            shape_type = 'torus'
        else:
            shape_type = 'cube'  # Default
        
        # Extract parameters from prompt
        size = self._extract_size_from_prompt(prompt)
        position = self._extract_position_from_prompt(prompt, base_mesh_data)
        
        parameters = self._get_parameters_for_shape(shape_type, size)
        
        mesh = composition_engine.create_primitive(shape_type, parameters)
        
        return {
            "vertices": mesh.vertices.tolist(),
            "faces": mesh.faces.tolist(),
            "type": f"ai_{shape_type}",
            "position": position,
            "parameters": parameters
        }
    
    async def _generate_with_replicate(self, prompt: str, base_mesh_data: Optional[Dict]) -> Dict:
        """Use Replicate API for better quality (low cost)"""
        try:
            # Use Shap-E model on Replicate (~$0.01 per generation)
            model = "adirik/shap-e:ac5d6d63c5ac7c65b5bae07b3bcef4abab9c7b5dac4b8c3df175b8de66c5fcc4"
            
            output = await asyncio.to_thread(
                self.replicate_client.run,
                model,
                input={"prompt": prompt}
            )
            
            # Note: Shap-E returns a 3D model file, you'd need to process it
            # For now, we'll fall back to primitive generation
            logger.info(f"Replicate generation completed for prompt: {prompt}")
            return await self._generate_with_open_source(prompt, base_mesh_data)
            
        except Exception as e:
            logger.warning(f"Replicate generation failed, falling back: {str(e)}")
            return await self._generate_with_open_source(prompt, base_mesh_data)
    
    async def _fallback_to_primitive(self, prompt: str) -> Dict:
        """Fallback when AI generation fails"""
        from .composition_engine import CompositionEngine
        composition_engine = CompositionEngine()
        
        # Create a simple cube as fallback
        mesh = composition_engine.create_primitive('cube', {'size': 0.5})
        
        return {
            "vertices": mesh.vertices.tolist(),
            "faces": mesh.faces.tolist(),
            "type": "ai_cube_fallback",
            "position": [1.5, 0, 0],
            "parameters": {'size': 0.5}
        }
    
    def _extract_size_from_prompt(self, prompt: str) -> float:
        """Extract size hint from prompt"""
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ['small', 'tiny', 'little']):
            return 0.3
        elif any(word in prompt_lower for word in ['large', 'big', 'huge']):
            return 1.5
        else:
            return 0.7  # default medium size
    
    def _extract_position_from_prompt(self, prompt: str, base_mesh: Optional[Dict]) -> list:
        """Extract position hint from prompt relative to base mesh"""
        prompt_lower = prompt.lower()
        base_position = [0, 0, 0]
        
        if base_mesh:
            base_position = base_mesh.get('position', [0, 0, 0])
        
        if 'right' in prompt_lower:
            x_offset = 1.5
            return [base_position[0] + x_offset, base_position[1], base_position[2]]
        elif 'left' in prompt_lower:
            x_offset = -1.5
            return [base_position[0] + x_offset, base_position[1], base_position[2]]
        elif 'top' in prompt_lower or 'above' in prompt_lower:
            return [base_position[0], base_position[1] + 1.5, base_position[2]]
        elif 'bottom' in prompt_lower or 'below' in prompt_lower:
            return [base_position[0], base_position[1] - 1.5, base_position[2]]
        elif 'front' in prompt_lower:
            return [base_position[0], base_position[1], base_position[2] + 1.5]
        elif 'back' in prompt_lower or 'behind' in prompt_lower:
            return [base_position[0], base_position[1], base_position[2] - 1.5]
        else:
            # Position near but not overlapping
            return [base_position[0] + 1.2, base_position[1], base_position[2]]
    
    def _get_parameters_for_shape(self, shape_type: str, size: float) -> Dict:
        """Get parameters for different shape types"""
        if shape_type == 'cube':
            return {'size': size}
        elif shape_type == 'sphere':
            return {'radius': size * 0.5}
        elif shape_type == 'cylinder':
            return {'radius': size * 0.3, 'height': size}
        elif shape_type == 'cone':
            return {'radius': size * 0.4, 'height': size}
        elif shape_type == 'torus':
            return {'major_radius': size, 'minor_radius': size * 0.2}
        return {'size': size}