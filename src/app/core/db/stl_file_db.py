from typing import List, Optional, Dict, Any
from datetime import datetime
from .database import supabase
from .models import (
    UploadedModel, UploadedModelCreate, Component, ComponentCreate, 
    AnalysisResult, AnalysisStatus
)
import uuid
import json

class ModelCRUD:
    def __init__(self):
        self.client = supabase.get_client()
    
    async def create_model(self, model: UploadedModelCreate) -> UploadedModel:
        """Create a new model record with components"""
        model_data = model.dict(exclude={'components'})
        model_data['id'] = str(uuid.uuid4())
        model_data['upload_date'] = datetime.utcnow().isoformat()
        
        response = self.client.table('models').insert(model_data).execute()
        
        if not response.data:
            raise Exception("Failed to create model")
        
        created_model = UploadedModel(**response.data[0])
        
        # Create components if provided
        if model.components:
            components_crud = ComponentCRUD()
            for component_data in model.components:
                await components_crud.create_component(component_data, created_model.id)
            
            # Fetch the model with components
            created_model = await self.get_model(created_model.id)
        
        return created_model
    
    async def get_model(self, model_id: str) -> Optional[UploadedModel]:
        """Get a model by ID with components and analysis results"""
        # Get model
        model_response = self.client.table('models').select('*').eq('id', model_id).execute()
        
        if not model_response.data:
            return None
        
        model_data = model_response.data[0]
        
        # Get components
        components_crud = ComponentCRUD()
        components = await components_crud.get_components_by_model(model_id)
        model_data['components'] = components
        
        # Get analysis results
        analysis_crud = AnalysisCRUD()
        analysis_results = await analysis_crud.get_results_by_model(model_id)
        model_data['analysis_results'] = analysis_results
        
        return UploadedModel(**model_data)
    
    async def get_all_models(self, limit: int = 100, offset: int = 0) -> List[UploadedModel]:
        """Get all models with pagination"""
        response = self.client.table('models')\
            .select('*')\
            .order('upload_date', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        models = []
        for item in response.data:
            model = await self.get_model(item['id'])
            models.append(model)
        
        return models
    
    async def update_model(self, model_id: str, update_data: Dict[str, Any]) -> Optional[UploadedModel]:
        """Update model data"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = self.client.table('models')\
            .update(update_data)\
            .eq('id', model_id)\
            .execute()
        
        if not response.data:
            return None
        
        return await self.get_model(model_id)
    
    async def update_model_status(self, model_id: str, status: AnalysisStatus) -> Optional[UploadedModel]:
        """Update model analysis status"""
        return await self.update_model(model_id, {'analysis_status': status})
    
    async def update_last_opened(self, model_id: str) -> Optional[UploadedModel]:
        """Update last opened timestamp"""
        return await self.update_model(model_id, {'last_opened': datetime.utcnow().isoformat()})
    
    async def delete_model(self, model_id: str) -> bool:
        """Delete a model and its components"""
        response = self.client.table('models').delete().eq('id', model_id).execute()
        return len(response.data) > 0

class ComponentCRUD:
    def __init__(self):
        self.client = supabase.get_client()
    
    async def create_component(self, component: ComponentCreate, model_id: str) -> Component:
        """Create a new component for a model"""
        component_data = component.dict()
        component_data['id'] = str(uuid.uuid4())
        component_data['model_id'] = model_id
        
        response = self.client.table('components').insert(component_data).execute()
        
        if not response.data:
            raise Exception("Failed to create component")
        
        return Component(**response.data[0])
    
    async def get_component(self, component_id: str) -> Optional[Component]:
        """Get a component by ID"""
        response = self.client.table('components').select('*').eq('id', component_id).execute()
        
        if not response.data:
            return None
        
        return Component(**response.data[0])
    
    async def get_components_by_model(self, model_id: str) -> List[Component]:
        """Get all components for a model"""
        response = self.client.table('components')\
            .select('*')\
            .eq('model_id', model_id)\
            .order('name')\
            .execute()
        
        return [Component(**item) for item in response.data]
    
    async def update_component(self, component_id: str, update_data: Dict[str, Any]) -> Optional[Component]:
        """Update component data"""
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = self.client.table('components')\
            .update(update_data)\
            .eq('id', component_id)\
            .execute()
        
        if not response.data:
            return None
        
        return await self.get_component(component_id)
    
    async def delete_component(self, component_id: str) -> bool:
        """Delete a component"""
        response = self.client.table('components').delete().eq('id', component_id).execute()
        return len(response.data) > 0

class AnalysisCRUD:
    def __init__(self):
        self.client = supabase.get_client()
    
    async def create_analysis_result(self, result: AnalysisResult) -> AnalysisResult:
        """Create analysis result for a component"""
        result_data = result.dict()
        result_data['id'] = str(uuid.uuid4())
        
        response = self.client.table('analysis_results').insert(result_data).execute()
        
        if not response.data:
            raise Exception("Failed to create analysis result")
        
        return AnalysisResult(**response.data[0])
    
    async def get_results_by_component(self, component_id: str) -> List[AnalysisResult]:
        """Get analysis results for a component"""
        response = self.client.table('analysis_results')\
            .select('*')\
            .eq('component_id', component_id)\
            .order('created_at', desc=True)\
            .execute()
        
        return [AnalysisResult(**item) for item in response.data]
    
    async def get_results_by_model(self, model_id: str) -> List[AnalysisResult]:
        """Get all analysis results for a model"""
        # First get all component IDs for the model
        components_response = self.client.table('components')\
            .select('id')\
            .eq('model_id', model_id)\
            .execute()
        
        component_ids = [comp['id'] for comp in components_response.data]
        
        if not component_ids:
            return []
        
        # Get analysis results for all components
        response = self.client.table('analysis_results')\
            .select('*')\
            .in_('component_id', component_ids)\
            .execute()
        
        return [AnalysisResult(**item) for item in response.data]

# Create global instances
model_crud = ModelCRUD()
component_crud = ComponentCRUD()
analysis_crud = AnalysisCRUD()
storage_crud = StorageCRUD()  # Keep the existing storage CRUD