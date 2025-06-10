# src/audio/processor.py
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import io
import wave
from typing import List, Tuple, Optional
from src.utils.logger import logger
from src.utils.config import settings


class AudioProcessor:
    """Clase para procesar audio capturado"""
    
    def __init__(self):
        self.sample_rate = settings.audio.sample_rate
        self.channels = settings.audio.channels
        
        # Buffer para acumular audio
        self.audio_buffer = []
        self.buffer_duration = 0.0
        
        # Configuración de procesamiento
        self.silence_threshold = -40  # dB
        self.min_silence_duration = 1000  # ms
        self.target_duration = settings.transcription.interval_seconds
        
    def add_chunk(self, audio_data: np.ndarray, duration: float):
        """Agregar chunk de audio al buffer"""
        self.audio_buffer.append(audio_data)
        self.buffer_duration += duration
        
    def get_buffer_duration(self) -> float:
        """Obtener duración actual del buffer"""
        return self.buffer_duration
    
    def process_buffer(self) -> Optional[bytes]:
        """Procesar buffer de audio y retornar audio WAV"""
        if not self.audio_buffer:
            return None
        
        try:
            # Concatenar todos los chunks
            audio_data = np.concatenate(self.audio_buffer)
            
            # Convertir a bytes WAV
            wav_bytes = self._numpy_to_wav(audio_data)
            
            # Limpiar buffer
            self.clear_buffer()
            
            return wav_bytes
            
        except Exception as e:
            logger.error(f"Error procesando buffer: {str(e)}")
            return None
    
    def _numpy_to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convertir numpy array a bytes WAV"""
        buffer = io.BytesIO()
        
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        buffer.seek(0)
        return buffer.read()
    
    def detect_speech_segments(self, audio_bytes: bytes) -> List[Tuple[int, int]]:
        """Detectar segmentos con voz en el audio"""
        try:
            # Cargar audio con pydub
            audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
            
            # Detectar segmentos no silenciosos
            segments = detect_nonsilent(
                audio,
                min_silence_len=self.min_silence_duration,
                silence_thresh=self.silence_threshold,
                seek_step=10
            )
            
            return segments
            
        except Exception as e:
            logger.error(f"Error detectando segmentos: {str(e)}")
            return []
    
    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalizar volumen del audio"""
        if len(audio_data) == 0:
            return audio_data
        
        # Calcular máximo absoluto
        max_val = np.max(np.abs(audio_data))
        
        if max_val > 0:
            # Normalizar a 90% del rango máximo
            normalized = (audio_data / max_val * 0.9 * 32767).astype(np.int16)
            return normalized
        
        return audio_data
    
    def apply_noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """Aplicar reducción básica de ruido"""
        # Implementación simple usando filtro de media móvil
        window_size = 5
        if len(audio_data) > window_size:
            # Aplicar filtro de media móvil
            filtered = np.convolve(audio_data, np.ones(window_size)/window_size, mode='same')
            return filtered.astype(np.int16)
        
        return audio_data
    
    def clear_buffer(self):
        """Limpiar buffer de audio"""
        self.audio_buffer = []
        self.buffer_duration = 0.0
    
    def save_audio_to_file(self, audio_bytes: bytes, filename: str):
        """Guardar audio en archivo"""
        try:
            with open(filename, 'wb') as f:
                f.write(audio_bytes)
            logger.info(f"Audio guardado en: {filename}")
        except Exception as e:
            logger.error(f"Error guardando audio: {str(e)}")
            