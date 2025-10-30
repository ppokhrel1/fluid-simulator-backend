"""3D Model labeling endpoints."""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.security import get_current_user
from ...crud.crud_labels import label_crud
from ...crud.crud_stl_model import model_crud
from ...models.user import User
from ...schemas.labels import LabelCreate, LabelUpdate, LabelRead, AILabelSuggestion

router = APIRouter()

def extract_list(result):
    # tuple: (list, count)
    if isinstance(result, tuple):
        return result[0]

    # dict pagination shape: {"data": [...], "total_count": N}
    if isinstance(result, dict) and "data" in result:
        return result["data"]

    # otherwise return as-is (if it's already a list)
    return result

@router.get("/models/{model_id}/labels", response_model=List[LabelRead])
async def get_model_labels(
    model_id: str,
    db: AsyncSession = Depends(async_get_db)
):
    """Get all labels for a specific 3D model."""
    # Verify model exists
    model = await stl_models.get(db, id=model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    labels = await label_crud.get_model_labels(db, model_id)
    return extract_list(labels)


@router.post("/models/{model_id}/labels", response_model=LabelRead)
async def create_model_label(
    model_id: str,
    label_data: LabelCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new label for a 3D model."""
    # Verify model exists
    model = await stl_models.get(db, id=model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    label_dict = label_data.model_dump()
    label_dict["model_id"] = model_id
    label_dict["created_by"] = current_user.id
    
    label = await label_crud.create(db, obj_in=label_dict)
    return label


@router.get("/labels/{label_id}", response_model=LabelRead)
async def get_label(
    label_id: str,
    db: AsyncSession = Depends(async_get_db)
):
    """Get a specific label."""
    label = await label_crud.get(db, id=label_id)
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found"
        )
    return label


@router.put("/labels/{label_id}", response_model=LabelRead)
async def update_label(
    label_id: str,
    label_update: LabelUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a label (only by creator)."""
    label = await label_crud.get(db, id=label_id)
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found"
        )
    
    if label.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can update this label"
        )
    
    updated_label = await label_crud.update(db, db_obj=label, obj_in=label_update)
    return updated_label


@router.delete("/labels/{label_id}")
async def delete_label(
    label_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a label (only by creator)."""
    label = await label_crud.get(db, id=label_id)
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found"
        )
    
    if label.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete this label"
        )
    
    await label_crud.remove(db, id=label_id)
    return {"message": "Label deleted successfully"}


@router.get("/labels/user/{user_id}", response_model=List[LabelRead])
async def get_user_labels(
    user_id: int,
    db: AsyncSession = Depends(async_get_db)
):
    """Get all labels created by a specific user."""
    labels = await label_crud.get_user_labels(db, user_id)
    return labels


@router.get("/labels/category/{category}", response_model=List[LabelRead])
async def get_labels_by_category(
    category: str,
    db: AsyncSession = Depends(async_get_db)
):
    """Get labels by category."""
    labels = await label_crud.get_labels_by_category(db, category)
    return extract_list(labels)


@router.post("/models/{model_id}/ai-suggestions", response_model=List[AILabelSuggestion])
async def get_ai_label_suggestions(
    model_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI-powered label suggestions for a 3D model."""
    # Verify model exists
    model = await stl_models.get(db, id=model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # TODO: Integrate with AI service for model analysis
    # For now, return mock suggestions
    mock_suggestions = [
        AILabelSuggestion(
            label_text="Base",
            category="structural",
            confidence=0.95,
            suggested_position={"x": 0.0, "y": 0.0, "z": 0.0},
            description="The foundation or base of the model"
        ),
        AILabelSuggestion(
            label_text="Top Surface",
            category="surface",
            confidence=0.88,
            suggested_position={"x": 0.0, "y": 0.0, "z": 10.0},
            description="The upper surface of the model"
        ),
        AILabelSuggestion(
            label_text="Edge Detail",
            category="detail",
            confidence=0.72,
            suggested_position={"x": 5.0, "y": 5.0, "z": 5.0},
            description="Notable edge or corner feature"
        )
    ]
    
    return extract_list(mock_suggestions)
