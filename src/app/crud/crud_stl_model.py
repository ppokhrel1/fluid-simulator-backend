from fastcrud import FastCRUD
from ..models.stl_models import UploadedModel, Component, AnalysisResult
from ..schemas.stl_file_models import (
    UploadedModelCreate, UploadedModelUpdate, UploadedModelDelete, UploadedModelRead,
    ComponentCreate, ComponentUpdate, ComponentDelete, ComponentRead,
    AnalysisResultCreate, AnalysisResultUpdate, AnalysisResultDelete, AnalysisResultRead
)

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

# -------------------- Storage CRUD (placeholder) --------------------
# You can implement your own storage interface (S3, local, etc.)
storage_crud = None
