# app/models/oauth.py
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseOAuthAccountTable
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import ForeignKey
import uuid as uuid_pkg

from src.app.core.db.database import Base

class OAuthAccount(SQLAlchemyBaseOAuthAccountTable, Base):
    __tablename__ = "oauth_account"

    user_id: Mapped[uuid_pkg.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="cascade"), 
        nullable=False
    )
    
    user: Mapped["User"] = relationship("User", lazy="joined")