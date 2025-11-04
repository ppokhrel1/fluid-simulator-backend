from fastcrud import FastCRUD

from src.app.models.user import User
from src.app.schemas.user import UserCreateInternal, UserDelete, UserRead, UserUpdate, UserUpdateInternal

CRUDUser = FastCRUD[User, UserCreateInternal, UserUpdate, UserUpdateInternal, UserDelete, UserRead]
crud_users = CRUDUser(User)
