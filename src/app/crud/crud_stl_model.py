from fastcrud import FastCRUD
from src.app.models.stl_models import UploadedModel, Component, AnalysisResult
from src.app.schemas.stl_file_models import (
    UploadedModelCreate, UploadedModelUpdate, UploadedModelDelete, UploadedModelRead,
    ComponentCreate, ComponentUpdate, ComponentDelete, ComponentRead,
    AnalysisResultCreate, AnalysisResultUpdate, AnalysisResultDelete, AnalysisResultRead
)
from .storage_handler import StorageCRUD
import os
# -------------------- CRUD for Models --------------------
CRUDModel = FastCRUD[
    UploadedModel,          # SQLAlchemy model
    UploadedModelCreate,    # Schema used for creation
    UploadedModelUpdate,    # Schema used for update
    UploadedModelUpdate,    # Schema used for partial update (can reuse same as update)
    UploadedModelDelete,    # Schema used for deletion
    UploadedModelRead       # Schema used for reading
]
model_crud = CRUDModel(UploadedModel)

# -------------------- CRUD for Components --------------------
CRUDComponent = FastCRUD[
    Component,
    ComponentCreate,
    ComponentUpdate,
    ComponentUpdate,
    ComponentDelete,
    ComponentRead
]
component_crud = CRUDComponent(Component)

# -------------------- CRUD for Analysis Results --------------------
CRUDAnalysis = FastCRUD[
    AnalysisResult,
    AnalysisResultCreate,
    AnalysisResultUpdate,
    AnalysisResultUpdate,
    AnalysisResultDelete,
    AnalysisResultRead
]
analysis_crud = CRUDAnalysis(AnalysisResult)
from src.app.core.config import settings

# -------------------- Storage CRUD (placeholder) --------------------
# You can implement your own storage interface (S3, local, etc.)
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
BUCKET_NAME = settings.SUPABASE_BUCKET_NAME
if not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = "https://" + SUPABASE_URL
print("Supabase KEY:", SUPABASE_KEY)
# Initialize the storage CRUD instance
storage_crud = StorageCRUD(
    supabase_url=SUPABASE_URL,
    supabase_key=SUPABASE_KEY,
    bucket_name=BUCKET_NAME
)