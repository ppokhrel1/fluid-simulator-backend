"""CRUD operations for chatbot system."""

from typing import List, Optional
from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from src.app.models.chatbot import ChatSession, ChatHistory
from src.app.schemas.chatbot import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionUpdateInternal, ChatSessionDelete, ChatSessionRead,
    ChatHistoryCreate, ChatHistoryUpdate, ChatHistoryUpdateInternal, ChatHistoryDelete, ChatHistoryRead
)


CRUDChatSession = FastCRUD[ChatSession, ChatSessionCreate, ChatSessionUpdate, ChatSessionUpdateInternal, ChatSessionDelete, ChatSessionRead]

class ChatSessionCRUD(CRUDChatSession):
    async def get_user_sessions(self, db: AsyncSession, user_id: int) -> List[ChatSession]:
        """Get all chat sessions for a user."""
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .options(selectinload(self.model.chat_history))
            .order_by(desc(self.model.created_at))
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_session_with_history(self, db: AsyncSession, session_id: str) -> Optional[ChatSession]:
        """Get a chat session with its full chat history."""
        stmt = (
            select(self.model)
            .where(self.model.id == session_id)
            .options(selectinload(self.model.chat_history))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


CRUDChatHistory = FastCRUD[ChatHistory, ChatHistoryCreate, ChatHistoryUpdate, ChatHistoryUpdateInternal, ChatHistoryDelete, ChatHistoryRead]

class ChatHistoryCRUD(CRUDChatHistory):
    async def get_session_messages(
        self, 
        db: AsyncSession, 
        session_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[ChatHistory]:
        """Get chat messages for a session."""
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at)
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_latest_messages(
        self, 
        db: AsyncSession, 
        session_id: str, 
        count: int = 10
    ) -> List[ChatHistory]:
        """Get the latest messages from a chat session."""
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(desc(self.model.created_at))
            .limit(count)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        return list(reversed(messages))  # Return in chronological order


# Create instances
chat_session_crud = ChatSessionCRUD(ChatSession)
chat_history_crud = ChatHistoryCRUD(ChatHistory)