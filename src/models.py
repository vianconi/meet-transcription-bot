# src/models.py
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship


class Meeting(SQLModel, table=True):
    """Modelo para almacenar información de reuniones"""
    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_url: str = Field(index=True)
    title: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    participant_count: Optional[int] = None
    status: str = Field(default="active")  # active, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relaciones
    transcriptions: List["Transcription"] = Relationship(back_populates="meeting")


class Transcription(SQLModel, table=True):
    """Modelo para almacenar transcripciones"""
    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meeting.id")
    timestamp: datetime
    speaker: Optional[str] = None
    text: str
    confidence: Optional[float] = None
    audio_file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relaciones
    meeting: Optional[Meeting] = Relationship(back_populates="transcriptions")


class TranscriptionStats(SQLModel, table=True):
    """Modelo para estadísticas de transcripción"""
    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meeting.id")
    total_words: int = 0
    total_speakers: int = 0
    average_confidence: float = 0.0
    processing_time_seconds: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    