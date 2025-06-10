# src/audio/capture.py

import asyncio
import threading
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
import pyaudio
import wave
import os
from datetime import datetime
import logging
import time
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Representa un chunk de audio con metadatos"""
    data: bytes
    timestamp: datetime
    duration: float
    sample_rate: int
    channels: int
    
    def to_numpy(self) -> np.ndarray:
        """Convierte el audio a numpy array"""
        return np.frombuffer(self.data, dtype=np.int16)


class AudioCapture:
    """Clase para capturar audio del micrófono"""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 chunk_size: int = 1024,
                 device_index: Optional[int] = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self._lock = threading.Lock()
        
    def start_capture(self, device_index: Optional[int] = None):
        """Inicia la captura de audio"""
        with self._lock:
            if self.is_recording:
                return
            
            # Usar el device_index proporcionado o el del constructor
            device_to_use = device_index if device_index is not None else self.device_index
                
            try:
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=device_to_use,
                    frames_per_buffer=self.chunk_size
                )
                self.is_recording = True
                logger.info(f"Captura iniciada (dispositivo: {device_to_use})")
            except Exception as e:
                logger.error(f"Error iniciando captura: {e}")
                raise
                
    def stop_capture(self):
        """Detiene la captura de audio"""
        with self._lock:
            if not self.is_recording:
                return
                
            self.is_recording = False
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                
            logger.info("Captura detenida")
            
    def read_chunk(self) -> Optional[AudioChunk]:
        """Lee un chunk de audio"""
        if not self.is_recording or not self.stream:
            return None
            
        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            
            duration = len(data) / (self.sample_rate * self.channels * 2)  # 2 bytes per sample
            
            return AudioChunk(
                data=data,
                timestamp=datetime.now(),
                duration=duration,
                sample_rate=self.sample_rate,
                channels=self.channels
            )
        except Exception as e:
            logger.error(f"Error leyendo audio: {e}")
            return None
            
    def list_audio_devices(self) -> List[Dict[str, Any]]:
        """Lista todos los dispositivos de audio disponibles"""
        devices = []
        
        logger.info("Dispositivos de audio disponibles:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # Solo dispositivos de entrada
                device_info = {
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'rate': info['defaultSampleRate']
                }
                devices.append(device_info)
                logger.info(f"  [{i}] {info['name']} - Canales: {info['maxInputChannels']} - Rate: {info['defaultSampleRate']}")
        
        return devices
    
    # Alias para compatibilidad
    start = start_capture
    stop = stop_capture
            
    def __del__(self):
        """Limpieza al destruir el objeto"""
        self.stop_capture()
        if hasattr(self, 'audio'):
            self.audio.terminate()


class AudioManager:
    """Manager para grabar y procesar audio con transcripción"""
    
    def __init__(self, meeting_id: str, transcriber, output_dir: str = "output/audio"):
        self.meeting_id = meeting_id
        self.transcriber = transcriber
        self.output_dir = output_dir
        self.is_recording = False
        self.audio_thread = None
        self.transcription_thread = None
        self.current_audio_data = []
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Crear directorio si no existe
        os.makedirs(self.output_dir, exist_ok=True)
        
    def start_recording(self, device_index: Optional[int] = None, 
                       transcription_interval: int = 5,
                       on_transcription: Optional[Callable] = None):
        """Inicia la grabación y transcripción periódica"""
        if self.is_recording:
            return
            
        self.is_recording = True
        self.on_transcription = on_transcription
        
        # Iniciar thread de grabación
        self.audio_thread = threading.Thread(
            target=self._record_audio,
            args=(device_index,)
        )
        self.audio_thread.start()
        
        # Iniciar thread de transcripción periódica
        self.transcription_thread = threading.Thread(
            target=self._periodic_transcription,
            args=(transcription_interval,)
        )
        self.transcription_thread.start()
        
        logger.info(f"AudioManager iniciado para reunión {self.meeting_id}")
        
    def _record_audio(self, device_index: Optional[int] = None):
        """Thread para grabar audio continuamente"""
        try:
            # Configurar stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
            
            logger.info(f"Captura de audio iniciada (dispositivo: {device_index})")
            
            while self.is_recording:
                try:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    self.current_audio_data.append(data)
                except Exception as e:
                    logger.error(f"Error leyendo audio: {e}")
                    
        except Exception as e:
            logger.error(f"Error iniciando captura: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                
    def _periodic_transcription(self, interval: int):
        """Thread para transcribir periódicamente"""
        while self.is_recording:
            time.sleep(interval)
            if self.current_audio_data:
                self._process_audio_chunk()
                
    def _process_audio_chunk(self):
        """Procesa y transcribe el chunk de audio actual"""
        if not self.current_audio_data:
            return
            
        # Copiar y limpiar datos
        audio_data = self.current_audio_data.copy()
        self.current_audio_data = []
        
        # Guardar audio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meeting_{self.meeting_id}_{timestamp}.wav"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(audio_data))
                
            logger.info(f"Audio guardado en: {filepath}")
            
            # Transcribir - Usar asyncio.run() para ejecutar la función asíncrona
            try:
                transcription = asyncio.run(self._transcribe_audio_file(filepath))
                if self.on_transcription and transcription:
                    self.on_transcription(transcription, timestamp)
            except Exception as e:
                logger.error(f"Error en transcripción: {e}")
                
        except Exception as e:
            logger.error(f"Error procesando audio: {str(e)}")
            
    async def _transcribe_audio_file(self, filepath: str) -> Optional[str]:
        """Transcribe un archivo de audio"""
        try:
            result = await self.transcriber.transcribe(filepath)
            if result and result.text:
                return result.text.strip()
        except Exception as e:
            logger.error(f"Error transcribiendo: {e}")
        return None
        
    def stop_recording(self):
        """Detiene la grabación"""
        self.is_recording = False
        
        if self.audio_thread:
            self.audio_thread.join()
            
        if self.transcription_thread:
            self.transcription_thread.join()
            
        # Procesar audio restante
        if self.current_audio_data:
            self._process_audio_chunk()
            
        logger.info("AudioManager detenido")
        
    def __del__(self):
        """Limpieza al destruir el objeto"""
        if hasattr(self, 'audio'):
            self.audio.terminate()


# Funciones auxiliares
def capture_audio_with_transcription(
    transcriber,
    duration: int = 20,
    device_index: Optional[int] = None,
    transcription_interval: int = 5
) -> List[str]:
    """
    Captura audio con transcripción periódica
    """
    transcriptions = []
    
    def on_transcription(text: str, timestamp: str):
        print(f"\n📝 [{timestamp}] Transcripción: {text}")
        transcriptions.append(text)
    
    # Crear manager
    manager = AudioManager("1000", transcriber)
    
    # Iniciar grabación
    manager.start_recording(
        device_index=device_index,
        transcription_interval=transcription_interval,
        on_transcription=on_transcription
    )
    
    # Esperar duración especificada
    time.sleep(duration)
    
    # Detener
    manager.stop_recording()
    
    return transcriptions


def transcribe_audio_file(transcriber, audio_file: str) -> Optional[str]:
    """
    Transcribe un archivo de audio existente
    """
    try:
        # Usar asyncio.run() para ejecutar la función asíncrona
        async def _transcribe():
            result = await transcriber.transcribe(audio_file)
            return result.text.strip() if result and result.text else None
            
        return asyncio.run(_transcribe())
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {e}")
        return None


def list_audio_devices() -> List[Dict[str, Any]]:
    """Lista todos los dispositivos de audio disponibles"""
    p = pyaudio.PyAudio()
    devices = []
    
    logger.info("Dispositivos de audio disponibles:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:  # Solo dispositivos de entrada
            device_info = {
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'rate': info['defaultSampleRate']
            }
            devices.append(device_info)
            logger.info(f"  [{i}] {info['name']} - Canales: {info['maxInputChannels']} - Rate: {info['defaultSampleRate']}")
    
    p.terminate()
    return devices
