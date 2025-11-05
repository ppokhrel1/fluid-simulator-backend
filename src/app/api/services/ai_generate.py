# app/services/ai_generate.py
import replicate
import os
import asyncio
from typing import Dict, Optional
import logging
import re
import math
import random

from src.app.core.config import AppSettings, Settings

logger = logging.getLogger(__name__)

class AIGenerationService:
    def __init__(self):
        self.use_free_tier = Settings().USE_FREE_TIER == "true"
        
        if not self.use_free_tier and AppSettings().REPLICATE_API_TOKEN:
            self.replicate_client = replicate.Client(api_token=AppSettings().REPLICATE_API_TOKEN)
        else:
            self.replicate_client = None
    
    async def generate_shape_from_prompt(self, prompt: str, base_mesh_data: Optional[Dict] = None) -> Dict:
        """Generate 3D shape from text prompt"""
        print(f"🎯 AI Generation Request: '{prompt}'")
        print(f"🔍 Base mesh data: {base_mesh_data}")
        
        try:
            if self.use_free_tier or not self.replicate_client:
                result = await self._generate_with_enhanced_keywords(prompt, base_mesh_data)
                print(f"✅ Generated shape: {result['type']} at position {result['position']}")
                return result
            else:
                return await self._generate_with_replicate(prompt, base_mesh_data)
                
        except Exception as e:
            logger.error(f"AI generation failed: {str(e)}")
            print(f"❌ AI generation failed: {str(e)}")
            return await self._fallback_to_primitive(prompt)
    
    async def _generate_with_enhanced_keywords(self, prompt: str, base_mesh_data: Optional[Dict]) -> Dict:
        """Enhanced keyword-based generation with proper scaling"""
        from .composition_engine import CompositionEngine
        composition_engine = CompositionEngine()
        
        prompt_lower = prompt.lower()
        
        # Enhanced shape detection with priority scoring
        shape_type = self._detect_shape_type_advanced(prompt_lower)
        print(f"🔍 Detected shape type: {shape_type}")
        
        # Extract detailed parameters
        size_params = self._extract_detailed_parameters(prompt_lower)
        position = self._extract_position_from_prompt(prompt, base_mesh_data)
        
        # Merge parameters with PROPER SCALING
        parameters = {**self._get_scaled_parameters_for_shape(shape_type, size_params), **size_params}
        print(f"🔍 Final parameters: {parameters}")
        
        try:
            mesh = composition_engine.create_primitive(shape_type, parameters)
            
            return {
                "vertices": mesh.vertices.tolist(),
                "faces": mesh.faces.tolist(),
                "type": f"ai_{shape_type}",
                "position": position,
                "parameters": parameters
            }
        except Exception as e:
            logger.warning(f"Failed to create {shape_type}, falling back to cube: {str(e)}")
            print(f"⚠️ Failed to create {shape_type}, falling back to cube")
            # Fallback to cube if the detected shape fails
            mesh = composition_engine.create_primitive('cube', {'size': 4.0})
            return {
                "vertices": mesh.vertices.tolist(),
                "faces": mesh.faces.tolist(),
                "type": "ai_cube_fallback",
                "position": position,
                "parameters": {'size': 4.0}
            }
    
    def _detect_shape_type_advanced(self, prompt: str) -> str:
        """Advanced shape detection with scoring system"""
        shape_scores = {
            'cube': 0,
            'sphere': 0, 
            'cylinder': 0,
            'cone': 0,
            'torus': 0
        }
        
        # Shape keywords with weights
        shape_keywords = {
            'cube': [
                ('cube', 3), ('block', 3), ('box', 3), ('rectangular', 2), 
                ('square', 2), ('brick', 2), ('prism', 1)
            ],
            'sphere': [
                ('sphere', 3), ('ball', 3), ('globe', 3), ('round', 2), 
                ('orb', 2), ('bubble', 2), ('circle', 1)
            ],
            'cylinder': [
                ('cylinder', 3), ('tube', 3), ('pipe', 3), ('rod', 2),
                ('column', 2), ('barrel', 2), ('can', 2)
            ],
            'cone': [
                ('cone', 3), ('pyramid', 3), ('pointed', 2), ('triangular', 2),
                ('tapered', 2), ('peak', 1)
            ],
            'torus': [
                ('torus', 3), ('donut', 3), ('ring', 3), ('loop', 2),
                ('annular', 2), ('wheel', 1)
            ]
        }
        
        # Score each shape
        for shape, keywords in shape_keywords.items():
            for keyword, weight in keywords:
                if keyword in prompt:
                    shape_scores[shape] += weight
        
        # Check for negative indicators
        negative_indicators = {
            'cube': ['not cube', 'no cube', 'not block', 'no block'],
            'sphere': ['not sphere', 'no sphere', 'not round', 'no ball'],
            'cylinder': ['not cylinder', 'no cylinder', 'not tube', 'no pipe'],
            'cone': ['not cone', 'no cone', 'not pyramid', 'no pyramid'],
            'torus': ['not torus', 'no torus', 'not ring', 'no ring']
        }
        
        for shape, negatives in negative_indicators.items():
            for negative in negatives:
                if negative in prompt:
                    shape_scores[shape] = 0  # Veto this shape
        
        # Get shape with highest score
        best_shape = max(shape_scores, key=shape_scores.get)
        best_score = shape_scores[best_shape]
        
        # If no clear winner, use context-based fallback
        if best_score == 0:
            return self._context_based_fallback(prompt)
        
        logger.info(f"Detected shape: {best_shape} with score: {best_score}")
        return best_shape
    
    def _context_based_fallback(self, prompt: str) -> str:
        """Context-based fallback when no clear shape is detected"""
        # Check for mechanical/architectural context
        if any(word in prompt for word in ['mechanical', 'engine', 'gear', 'machine', 'building', 'house', 'wall']):
            return 'cube'
        
        # Check for organic/natural context  
        if any(word in prompt for word in ['organic', 'natural', 'plant', 'tree', 'rock', 'mountain']):
            return 'sphere'
        
        # Check for structural context
        if any(word in prompt for word in ['structural', 'support', 'beam', 'pillar']):
            return 'cylinder'
        
        # Default to cube as most versatile primitive
        return 'cube'
    
    def _extract_detailed_parameters(self, prompt: str) -> Dict:
        """Extract detailed parameters from prompt"""
        params = {}
        
        # Size extraction
        size_mapping = {
            'tiny': 0.5, 'small': 1.0, 'medium': 1.5, 'normal': 2.0,
            'large': 2.5, 'big': 2.5, 'huge': 3.0, 'massive': 3.5
        }
        
        for size_word, size_value in size_mapping.items():
            if size_word in prompt:
                params['base_size'] = size_value
                break
        else:
            params['base_size'] = 1.5  # default medium size
        
        # Dimension-specific parameters
        # Extract numbers from prompt (e.g., "2 meter", "5cm", "10 units")
        dimension_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:meter|m)(?:\s|$)', 'size'),
            (r'(\d+(?:\.\d+)?)\s*(?:centimeter|cm)(?:\s|$)', 'size_cm'),
            (r'(\d+(?:\.\d+)?)\s*(?:unit|units)(?:\s|$)', 'size_units'),
            (r'(\d+(?:\.\d+)?)\s*(?:foot|feet|ft)(?:\s|$)', 'size_ft')
        ]
        
        for pattern, param_name in dimension_patterns:
            match = re.search(pattern, prompt)
            if match:
                params[param_name] = float(match.group(1))
        
        # Aspect ratio detection
        if 'long' in prompt and 'thin' in prompt:
            params['aspect_ratio'] = 'long_thin'
        elif 'short' in prompt and 'wide' in prompt:
            params['aspect_ratio'] = 'short_wide'
        elif 'flat' in prompt:
            params['aspect_ratio'] = 'flat'
        
        return params
    
    def _get_scaled_parameters_for_shape(self, shape_type: str, size_params: Dict) -> Dict:
        """Get SCALED parameters to match your scene scale (4x scaling)"""
        # Your scene uses 4x scaling, so scale up the AI-generated objects
        SCENE_SCALE_FACTOR = 4.0
        base_size = size_params.get('base_size', 1.5)
        
        if shape_type == 'cube':
            size = size_params.get('size_units', base_size)
            return {'size': size * SCENE_SCALE_FACTOR}
            
        elif shape_type == 'sphere':
            radius = size_params.get('size_units', base_size * 0.5)
            subdivisions = 3 if base_size > 2.0 else 2
            return {'radius': radius * SCENE_SCALE_FACTOR, 'subdivisions': subdivisions}
            
        elif shape_type == 'cylinder':
            radius = size_params.get('size_units', base_size * 0.3)
            height = size_params.get('size_units', base_size)
            
            # Adjust for aspect ratio
            if size_params.get('aspect_ratio') == 'long_thin':
                height = height * 2
                radius = radius * 0.5
            elif size_params.get('aspect_ratio') == 'short_wide':
                height = height * 0.5
                radius = radius * 1.5
                
            return {
                'radius': radius * SCENE_SCALE_FACTOR, 
                'height': height * SCENE_SCALE_FACTOR
            }
            
        elif shape_type == 'cone':
            radius = size_params.get('size_units', base_size * 0.4)
            height = size_params.get('size_units', base_size)
            return {
                'radius': radius * SCENE_SCALE_FACTOR, 
                'height': height * SCENE_SCALE_FACTOR
            }
            
        elif shape_type == 'torus':
            major_radius = size_params.get('size_units', base_size)
            minor_radius = size_params.get('size_units', base_size * 0.2)
            return {
                'major_radius': major_radius * SCENE_SCALE_FACTOR,
                'minor_radius': minor_radius * SCENE_SCALE_FACTOR
            }
            
        return {'size': base_size * SCENE_SCALE_FACTOR}
    
    def _extract_position_from_prompt(self, prompt: str, base_mesh: Optional[Dict]) -> list:
        """Enhanced position extraction with REASONABLE distances"""
        prompt_lower = prompt.lower()
        base_position = [0, 0, 0]
        
        if base_mesh:
            base_position = base_mesh.get('position', [0, 0, 0])
            print(f"🔍 Base mesh position: {base_position}")
        
        # Use REASONABLE offset distances that work well in your scene
        # Much smaller offsets for better positioning
        base_offset = 1.5  # Base offset in scene units
        
        # Adjust offset based on size expectations
        if 'large' in prompt_lower or 'big' in prompt_lower:
            offset_distance = base_offset * 1.5
        elif 'small' in prompt_lower or 'tiny' in prompt_lower:
            offset_distance = base_offset * 0.7
        else:
            offset_distance = base_offset
        
        print(f"🔍 Offset distance: {offset_distance}")
        
        # Position extraction with multiple keywords
        position_offsets = {
            'right': [offset_distance, 0, 0],
            'left': [-offset_distance, 0, 0],
            'top': [0, offset_distance, 0],
            'above': [0, offset_distance, 0],
            'bottom': [0, -offset_distance, 0],
            'below': [0, -offset_distance, 0],
            'under': [0, -offset_distance, 0],
            'front': [0, 0, offset_distance],
            'forward': [0, 0, offset_distance],
            'back': [0, 0, -offset_distance],
            'behind': [0, 0, -offset_distance],
            'side': [offset_distance, 0, 0],
            'center': [0, 0, 0],
            'middle': [0, 0, 0],
        }
        
        # Check for position keywords
        for keyword, offset in position_offsets.items():
            if keyword in prompt_lower:
                final_position = [
                    base_position[0] + offset[0],
                    base_position[1] + offset[1], 
                    base_position[2] + offset[2]
                ]
                print(f"🔍 Position from '{keyword}': {final_position}")
                return final_position
        
        # If no specific position, place it nearby but not overlapping
        # Use smaller random offset for default positioning
        angle = random.uniform(0, 2 * math.pi)
        distance = offset_distance * 0.8  # Smaller default distance
        
        default_position = [
            base_position[0] + math.cos(angle) * distance,
            base_position[1] + 0.5,  # Slight vertical offset
            base_position[2] + math.sin(angle) * distance
        ]
        print(f"🔍 Default position: {default_position}")
        return default_position
    
    async def _generate_with_replicate(self, prompt: str, base_mesh_data: Optional[Dict]) -> Dict:
        """Use Replicate API with enhanced error handling"""
        try:
            if not self.replicate_client:
                raise Exception("Replicate client not available")
                
            # Use newer 3D generation models
            model = "cjwbw/shap-e:5957069d5c509126a73c7cb68abcddbb985aeefa4d318e7c63ec1352ce6da68c"
            
            output = await asyncio.to_thread(
                self.replicate_client.run,
                model,
                input={"prompt": prompt, "guidance_scale": 15.0}
            )
            
            logger.info(f"Replicate generation completed for: {prompt}")
            
            # Process Replicate output (this would need to be adapted based on actual output format)
            # For now, fall back to enhanced keyword method
            return await self._generate_with_enhanced_keywords(prompt, base_mesh_data)
            
        except Exception as e:
            logger.warning(f"Replicate generation failed: {str(e)}")
            return await self._generate_with_enhanced_keywords(prompt, base_mesh_data)
    
    async def _fallback_to_primitive(self, prompt: str) -> Dict:
        """Enhanced fallback with context awareness"""
        from .composition_engine import CompositionEngine
        composition_engine = CompositionEngine()
        
        # Try to detect what went wrong and choose appropriate fallback
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['round', 'ball', 'sphere']):
            shape_type = 'sphere'
        elif any(word in prompt_lower for word in ['tube', 'pipe', 'cylinder']):
            shape_type = 'cylinder' 
        elif any(word in prompt_lower for word in ['cone', 'pyramid']):
            shape_type = 'cone'
        elif any(word in prompt_lower for word in ['ring', 'donut', 'torus']):
            shape_type = 'torus'
        else:
            shape_type = 'cube'
        
        # Use scaled parameters for fallback too
        parameters = self._get_scaled_parameters_for_shape(shape_type, {'base_size': 1.5})
        
        mesh = composition_engine.create_primitive(shape_type, parameters)
        
        # Use closer position for fallback
        return {
            "vertices": mesh.vertices.tolist(),
            "faces": mesh.faces.tolist(),
            "type": f"ai_{shape_type}_fallback",
            "position": [3.0, 0, 0],  # Much closer position
            "parameters": parameters
        }