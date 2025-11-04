"""Chatbot endpoints for AI model interaction."""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.db.database import async_get_db
from src.app.core.security import get_current_user
from src.app.crud.crud_chatbot import chat_session_crud, chat_history_crud
from src.app.models.user import User
from src.app.schemas.chatbot import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionRead,
    ChatHistoryCreate, ChatHistoryRead,
    ChatMessage, ChatResponse
)

def extract_list(result):
    # tuple: (list, count)
    if isinstance(result, tuple):
        return result[0]

    # dict pagination shape: {"data": [...], "total_count": N}
    if isinstance(result, dict) and "data" in result:
        return result["data"]

    # otherwise return as-is (if it's already a list)
    return result

router = APIRouter()



@router.get("/sessions", response_model=List[ChatSessionRead])
async def get_chat_sessions(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chat sessions for the current user."""
    sessions = await chat_session_crud.get_user_sessions(db, current_user.id)
    return extract_list(sessions)


@router.post("/sessions", response_model=ChatSessionRead)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat session."""
    session_dict = session_data.model_dump()
    session_dict["user_id"] = current_user.id
    session = await chat_session_crud.create(db, obj_in=session_dict)
    return extract_list(session)


@router.get("/sessions/{session_id}", response_model=ChatSessionRead)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat session with its history."""
    session = await chat_session_crud.get_session_with_history(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session"
        )
    
    return session


@router.put("/sessions/{session_id}", response_model=ChatSessionRead)
async def update_chat_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chat session."""
    session = await chat_session_crud.get(db, id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own chat sessions"
        )
    
    updated_session = await chat_session_crud.update(db, db_obj=session, obj_in=session_update)
    return updated_session


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat session."""
    session = await chat_session_crud.get(db, id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own chat sessions"
        )
    
    await chat_session_crud.remove(db, id=session_id)
    return {"message": "Chat session deleted successfully"}


@router.get("/sessions/{session_id}/messages", response_model=List[ChatHistoryRead])
async def get_chat_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat messages for a session."""
    # Verify session ownership
    session = await chat_session_crud.get(db, id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session"
        )
    
    messages = await chat_history_crud.get_session_messages(db, session_id, limit, offset)
    return extract_list(messages)


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_chat_message(
    session_id: str,
    message: ChatMessage,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to the AI chatbot."""
    # Verify session ownership
    session = await chat_session_crud.get(db, id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session"
        )
    
    # Save user message to history
    user_message_data = {
        "session_id": session_id,
        "message": message.message,
        "sender": "user",
        "message_type": message.message_type or "text"
    }
    
    user_message = await chat_history_crud.create(db, obj_in=user_message_data)
    
    # TODO: Integrate with AI service (OpenAI, Claude, etc.)
    # For now, return a mock response
    ai_response = f"I received your message: '{message.message}'. This is a placeholder response. AI integration coming soon!"
    
    # Save AI response to history
    ai_message_data = {
        "session_id": session_id,
        "message": ai_response,
        "sender": "assistant",
        "message_type": "text"
    }
    
    ai_message = await chat_history_crud.create(db, obj_in=ai_message_data)
    
    return ChatResponse(
        session_id=session_id,
        user_message=user_message,
        ai_response=ai_message,
        message="Message processed successfully"
    )
