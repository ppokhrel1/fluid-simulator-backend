from datetime import datetime
from typing import Annotated, ClassVar 
import json # Used in the validator logic

from pydantic import FieldValidationInfo
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, ValidationInfo, computed_field
from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema


class UserBase(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    username: Annotated[str, Field(min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    
    # 1. full_name remains a standard field
    full_name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    
    # Ensure this is set to handle SQLAlchemy properties/attributes
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class User(TimestampSchema, UserBase, UUIDSchema, PersistentDeletion):
    # Note: User inherits full_name and the model_config from UserBase
    profile_image_url: Annotated[str, Field(default="https://www.profileimageurl.com")]
    hashed_password: str
    is_superuser: bool = False
    tier_id: int | None = None


class UserRead(BaseModel):
    id: int
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    
    is_superuser: bool = False
    is_active: bool = True
    profile_image_url: str = "https://www.profileimageurl.com"
    tier_id: int | None = None
    
    # Config is now handled by model_config (Pydantic v2 style)
    model_config = ConfigDict(from_attributes=True)
    @computed_field
    @property
    def full_name(self) -> str:
        """Calculates full_name from the ORM object's 'name' attribute."""
        # This executes during serialization and pulls the value from self.name (which came from the ORM).
        return self.name

class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")

    password: Annotated[str, Field(pattern=r"^.{8,}|[0-9]+|[A-Z]+|[a-z]+|[^a-zA-Z0-9]+$", examples=["Str1ngst!"])]
    
    # NEW: Add a validator to ensure full_name is set equal to 'name' upon creation
    @field_validator('full_name', mode='before')
    @classmethod
    def sync_full_name_with_name(cls, v: str | None, info: FieldValidationInfo):
        if 'name' in info.data:
            return info.data['name']
        return v # Use provided value or rely on default/database

# NOTE: RegistrationRequest is frontend-compatible, so it must accept full_name as input.
class RegistrationRequest(BaseModel):
    """Frontend-compatible registration schema."""
    username: str
    email: EmailStr
    password: str
    full_name: str # Frontend sends this, which maps to UserBase.name/full_name


class UserCreateInternal(UserBase):
    hashed_password: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str | None, Field(min_length=2, max_length=30, examples=["User Userberg"], default=None)]
    username: Annotated[
        str | None, Field(min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userberg"], default=None)
    ]
    email: Annotated[EmailStr | None, Field(examples=["user.userberg@example.com"], default=None)]
    profile_image_url: Annotated[
        str | None,
        Field(
            pattern=r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", examples=["https://www.profileimageurl.com"], default=None
        ),
    ]
    # NEW: Allow updating full_name, which will update 'name' in the DB via UserBase logic
    full_name: Annotated[str | None, Field(min_length=2, max_length=30, examples=["User Userberg"], default=None)]


class UserUpdateInternal(UserUpdate):
    updated_at: datetime


class UserTierUpdate(BaseModel):
    tier_id: int


class UserDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime


class UserRestoreDeleted(BaseModel):
    is_deleted: bool