from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import io, json

from ...schemas.stl_file_models import (
    UploadedModelRead, UploadedModelCreate,
    ComponentRead, ComponentCreate,
    AnalysisResultRead, AnalysisResultCreate
)
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.db.database import async_get_db

from ...crud.crud_stl_model import model_crud, component_crud, analysis_crud, storage_crud
from ...api.dependencies import get_current_user, get_current_superuser
from ...models import User

router = APIRouter()

# -------------------- Models --------------------
@router.post("/upload", response_model=UploadedModelRead, status_code=201)
async def upload_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    web_link: Optional[str] = Form(None),
    tags: str = Form("[]"),
    thumbnail: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    designer: Optional[str] = Form(None),
    revision: Optional[str] = Form(None),
    units: Optional[str] = Form("meters"),
    scale_factor: Optional[float] = Form(1.0),
    fluid_density: Optional[float] = Form(1.225),
    fluid_viscosity: Optional[float] = Form(1.81e-5),
    velocity_inlet: Optional[float] = Form(None),
    temperature_inlet: Optional[float] = Form(None),
    pressure_outlet: Optional[float] = Form(None),
    components: str = Form("[]"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    """Upload a new 3D model with components and metadata"""
    allowed_types = ['stl', 'obj', 'glb', 'gltf', 'step', 'stp']
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type not supported. Allowed: {', '.join(allowed_types)}")

    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)

    try:
        tags_list = json.loads(tags)
        components_list = json.loads(components)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    model_data = UploadedModelCreate(
        name=name,
        file_name=file.filename,
        file_size=f"{file_size_mb:.2f} MB",
        file_type=file_extension,
        description=description,
        web_link=web_link,
        tags=tags_list,
        thumbnail=thumbnail,
        project_name=project_name,
        designer=designer,
        revision=revision,
        units=units,
        scale_factor=scale_factor,
        fluid_density=fluid_density,
        fluid_viscosity=fluid_viscosity,
        velocity_inlet=velocity_inlet,
        temperature_inlet=temperature_inlet,
        pressure_outlet=pressure_outlet,
        components=components_list,
        created_by_user_id=current_user.get('id') or current_user['id']
    )

    # FIX: Pass the 'db' session as the first argument to create
    model = await model_crud.create(db, model_data)
    await storage_crud.upload_file(file_content, file.filename, model.id)
    return model

@router.get("/", response_model=List[UploadedModelRead])
async def get_models(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    return await model_crud.get_all(db, limit=limit, offset=offset)

@router.get("/{model_id}", response_model=UploadedModelRead)
async def get_model(
    model_id: int, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    model = await model_crud.get(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    # FIX: Pass db
    await model_crud.update_last_opened(db, model_id)
    return model

@router.get("/{model_id}/download")
async def download_model(model_id: int, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)):
    # Assuming storage_crud doesn't require AsyncSession, but model_crud.get does.
    # FIX: Add db dependency to fetch model
    # Note: If model_id is 'int', this will fail later, but fixing the missing DB argument for now.
    model = await model_crud.get(db, model_id) 
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    file_content = await storage_crud.download_file(f"{model_id}/{model.file_name}")
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{model.file_name}"'}
    )

@router.put("/{model_id}/status", dependencies=[Depends(get_current_superuser)])
async def update_model_status(
    model_id: int, 
    status: str,
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    model = await model_crud.update_model_status(db, model_id, status)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model

@router.delete("/{model_id}", dependencies=[Depends(get_current_superuser)])
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    model = await model_crud.get(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    await storage_crud.delete_file(f"{model_id}/{model.file_name}")
    # FIX: Pass db
    await model_crud.delete(db, model_id)
    return {"success": True, "message": "Model deleted successfully"}

# -------------------- Components --------------------
@router.post("/{model_id}/components", response_model=ComponentRead, status_code=201)
async def create_component(
    model_id: int, 
    component: ComponentCreate, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    component.model_id = model_id
    # FIX: Pass db
    return await component_crud.create(db, component)

@router.get("/{model_id}/components", response_model=List[ComponentRead])
async def get_model_components(
    model_id: int, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    return await component_crud.get_all_by_model(db, model_id)

@router.put("/components/{component_id}", response_model=ComponentRead)
async def update_component(
    component_id: int, 
    update_data: Dict[str, Any] = Body(...), 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    component = await component_crud.update(db, component_id, update_data)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component

# -------------------- Analysis Results --------------------
@router.post("/analysis/results", response_model=AnalysisResultRead, status_code=201)
async def create_analysis_result(
    result: AnalysisResultCreate, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    return await analysis_crud.create(db, result)

@router.get("/components/{component_id}/analysis", response_model=List[AnalysisResultRead])
async def get_component_analysis(
    component_id: int, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db) # DB dependency injected
):
    # FIX: Pass db
    return await analysis_crud.get_all_by_component(db, component_id)