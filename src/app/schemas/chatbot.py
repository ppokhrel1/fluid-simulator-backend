"""AI Chatbot system Pydantic schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


# Chat Message Schemas
class ChatMessageOld(BaseModel):
    type: str  # user|ai
    content: str
    time: str
    file: Optional[Dict[str, Any]] = None


class FileData(BaseModel):
    name: str
    color: str
    icon: str
    size: Optional[str] = None
    file: Optional[Any] = None  # File object


class AIMessage(BaseModel):
    role: str  # user|assistant|system
    content: str


class AIAdapterOptions(BaseModel):
    apiUrl: Optional[str] = None
    apiKey: Optional[str] = None
    model: Optional[str] = None


# Chat Session Schemas
class ChatSessionBase(BaseModel):
    user_id: int
    model_id: Optional[int] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionUpdate(BaseModel):
    model_id: Optional[int] = None


class ChatSessionUpdateInternal(ChatSessionUpdate):
    pass


class ChatSessionDelete(BaseModel):
    pass


class ChatSessionRead(ChatSessionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Chat History Schemas
class ChatHistoryBase(BaseModel):
    session_id: str
    message_type: str  # user|ai
    content: str
    file_name: Optional[str] = None
    file_data: Optional[str] = None  # Base64 encoded


class ChatHistoryCreate(ChatHistoryBase):
    pass


class ChatHistoryUpdate(BaseModel):
    content: Optional[str] = None


class ChatHistoryUpdateInternal(ChatHistoryUpdate):
    pass


class ChatHistoryDelete(BaseModel):
    pass


class ChatHistoryRead(ChatHistoryBase):
    id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


# Combined Response Schemas
class ChatSessionWithMessages(ChatSessionRead):
    messages: List[ChatHistoryRead] = []


# API Request/Response Schemas
class ChatMessage(BaseModel):
    message: str
    message_type: Optional[str] = "text"


class ChatResponse(BaseModel):
    session_id: str
    user_message: ChatHistoryRead
    ai_response: ChatHistoryRead
    message: str