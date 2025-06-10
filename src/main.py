# src/main.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import uvicorn

from src.database import get_db, create_db_and_tables
from src.models import Meeting, Transcription, TranscriptionStats
from src.utils.config import settings
from src.utils.logger import logger
from src.audio.audio_manager import AudioManager

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Bot de transcripción automática para Google Meet"
)

# Crear instancia del audio manager
audio_manager = AudioManager()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Eventos de inicio/cierre
@app.on_event("startup")
async def startup_event():
    """Inicializar la aplicación"""
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    create_db_and_tables()
    logger.info("Base de datos inicializada")


@app.on_event("shutdown")
async def shutdown_event():
    """Cerrar la aplicación"""
    logger.info("Cerrando aplicación...")


# Rutas básicas
@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "active"
    }


@app.get("/health")
async def health_check():
    """Verificar estado de la aplicación"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Rutas para Meetings
@app.post("/meetings/", response_model=Meeting)
async def create_meeting(
    meeting_url: str,
    title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Crear una nueva reunión"""
    meeting = Meeting(meeting_url=meeting_url, title=title)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    logger.info(f"Reunión creada: {meeting.id}")
    return meeting


@app.get("/meetings/", response_model=List[Meeting])
async def get_meetings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Obtener lista de reuniones"""
    meetings = db.exec(select(Meeting).offset(skip).limit(limit)).all()
    return meetings


@app.get("/meetings/{meeting_id}", response_model=Meeting)
async def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Obtener una reunión específica"""
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Reunión no encontrada")
    return meeting


@app.post("/meetings/{meeting_id}/start")
async def start_transcription(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Iniciar transcripción de una reunión"""
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Reunión no encontrada")
    
    if meeting.status == "active":
        raise HTTPException(status_code=400, detail="La transcripción ya está activa")
    
    # Actualizar estado
    meeting.status = "active"
    meeting.start_time = datetime.utcnow()
    db.add(meeting)
    db.commit()
    
    # TODO: Agregar tarea en background para iniciar transcripción
    # background_tasks.add_task(start_transcription_task, meeting_id)
    
    return {"message": "Transcripción iniciada", "meeting_id": meeting_id}


@app.post("/meetings/{meeting_id}/stop")
async def stop_transcription(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Detener transcripción de una reunión"""
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Reunión no encontrada")
    
    if meeting.status != "active":
        raise HTTPException(status_code=400, detail="La transcripción no está activa")
    
    # Actualizar estado
    meeting.status = "completed"
    meeting.end_time = datetime.utcnow()
    if meeting.start_time:
        duration = (meeting.end_time - meeting.start_time).total_seconds()
        meeting.duration_seconds = int(duration)
    
    db.add(meeting)
    db.commit()
    
    # TODO: Implementar lógica para detener transcripción
    
    return {"message": "Transcripción detenida", "meeting_id": meeting_id}


# Rutas para Transcripciones
@app.get("/meetings/{meeting_id}/transcriptions", response_model=List[Transcription])
async def get_transcriptions(
    meeting_id: int,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Obtener transcripciones de una reunión"""
    transcriptions = db.exec(
        select(Transcription)
        .where(Transcription.meeting_id == meeting_id)
        .offset(skip)
        .limit(limit)
    ).all()
    return transcriptions


@app.post("/transcriptions/", response_model=Transcription)
async def create_transcription(
    meeting_id: int,
    text: str,
    timestamp: datetime,
    speaker: Optional[str] = None,
    confidence: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Crear una nueva transcripción"""
    transcription = Transcription(
        meeting_id=meeting_id,
        text=text,
        timestamp=timestamp,
        speaker=speaker,
        confidence=confidence
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    return transcription


# Rutas para Estadísticas
@app.get("/meetings/{meeting_id}/stats", response_model=TranscriptionStats)
async def get_meeting_stats(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Obtener estadísticas de una reunión"""
    stats = db.exec(
        select(TranscriptionStats)
        .where(TranscriptionStats.meeting_id == meeting_id)
    ).first()
    
    if not stats:
        raise HTTPException(status_code=404, detail="Estadísticas no encontradas")
    
    return stats

# ============= ENDPOINTS DE AUDIO =============

@app.get("/audio/devices")
async def list_audio_devices():
    """Listar dispositivos de audio disponibles"""
    devices = audio_manager.list_devices()
    return {"devices": devices}


@app.post("/meetings/{meeting_id}/audio/start")
async def start_audio_capture(
    meeting_id: int,
    device_index: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Iniciar captura de audio para una reunión"""
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Reunión no encontrada")
    
    try:
        audio_manager.start(meeting_id, device_index)
        return {"message": "Captura de audio iniciada", "meeting_id": meeting_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/meetings/{meeting_id}/audio/stop")
async def stop_audio_capture(meeting_id: int):
    """Detener captura de audio"""
    audio_manager.stop()
    return {"message": "Captura de audio detenida", "meeting_id": meeting_id}


@app.get("/audio/status")
async def get_audio_status():
    """Obtener estado de la captura de audio"""
    return {
        "is_active": audio_manager.is_active,
        "meeting_id": audio_manager.meeting_id,
        "audio_level": audio_manager.get_audio_level() if audio_manager.is_active else 0
    }


# Función principal
def main():
    """Ejecutar el servidor"""
    logger.info(f"Iniciando servidor en {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
    