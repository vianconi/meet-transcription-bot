# src/audio/audio_manager.py
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any  # Agregar List, Dict, Any
from src.audio.capture import AudioCapture, AudioChunk
from src.audio.processor import AudioProcessor
from src.utils.logger import logger
from src.transcription.engine import TranscriptionEngine
import asyncio


class AudioManager:
    """Manager principal para captura y procesamiento de audio"""
    
    def __init__(self, output_dir: str = "output/audio"):
        self.capture = AudioCapture()
        self.processor = AudioProcessor()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Agregar después de self.capture.on_audio_chunk = self._handle_audio_chunk
        self.transcription_engine = TranscriptionEngine()
        self.transcriptions = []
        
        # Estado
        self.is_active = False
        self.meeting_id: Optional[int] = None
        self.start_time: Optional[float] = None
        
        # Callbacks
        self.on_audio_ready: Optional[Callable[[bytes, float], None]] = None
        
        # Configurar callback de captura
        self.capture.on_audio_chunk = self._handle_audio_chunk
        
    def start(self, meeting_id: int, device_index: Optional[int] = None):
        """Iniciar captura y procesamiento de audio"""
        if self.is_active:
            logger.warning("AudioManager ya está activo")
            return
        
        self.meeting_id = meeting_id
        self.start_time = time.time()
        self.is_active = True
        
        # Iniciar captura
        self.capture.start_capture(device_index)
        logger.info(f"AudioManager iniciado para reunión {meeting_id}")
        
    def stop(self):
        """Detener captura y procesamiento"""
        if not self.is_active:
            return
        
        self.is_active = False
        self.capture.stop_capture()
        
        # Procesar audio restante
        if self.processor.get_buffer_duration() > 0:
            self._process_current_buffer()
        
        logger.info("AudioManager detenido")
        
    def _handle_audio_chunk(self, chunk: AudioChunk):
        """Manejar chunk de audio capturado"""
        if not self.is_active:
            return
        
        # Agregar al procesador
        self.processor.add_chunk(chunk.data, chunk.duration)
        
        # Verificar si es momento de procesar
        if self.processor.get_buffer_duration() >= self.processor.target_duration:
            self._process_current_buffer()
    
    def _process_current_buffer(self):
        """Procesar el buffer actual de audio"""
        # Obtener audio procesado
        audio_bytes = self.processor.process_buffer()
        
        if audio_bytes and len(audio_bytes) > 0:
            # Calcular timestamp relativo
            timestamp = time.time() - self.start_time if self.start_time else 0
            
            # Guardar archivo si está configurado
            if self.meeting_id:
                filename = self._generate_filename()
                filepath = self.output_dir / filename
                self.processor.save_audio_to_file(audio_bytes, str(filepath))

                # Transcribir audio
                asyncio.create_task(
                    self._transcribe_audio_file(str(filepath), timestamp)
)
            
            # Ejecutar callback
            if self.on_audio_ready:
                self.on_audio_ready(audio_bytes, timestamp)
    
    def _generate_filename(self) -> str:
        """Generar nombre de archivo para audio"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"meeting_{self.meeting_id}_{timestamp}.wav"
    
    def list_devices(self):
        """Listar dispositivos de audio disponibles"""
        return self.capture.list_audio_devices()
    
    def get_audio_level(self) -> float:
        """Obtener nivel actual de audio"""
        if self.processor.audio_buffer:
            last_chunk = self.processor.audio_buffer[-1]
            return self.capture.get_audio_level(last_chunk)
        return 0.0
    
    async def _transcribe_audio_file(self, audio_path: str, timestamp: float):
        """Transcribir archivo de audio"""
        try:
            result = await self.transcription_engine.transcribe_audio(audio_path)
            result["relative_timestamp"] = timestamp
            self.transcriptions.append(result)
            logger.info(f"Transcripción: {result.get('text', '[Sin texto]')}")
        except Exception as e:
            logger.error(f"Error en transcripción: {e}")

    def get_transcriptions(self) -> List[Dict[str, Any]]:
        """Obtener todas las transcripciones"""
        return self.transcriptions
    