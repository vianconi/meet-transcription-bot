# src/transcription/engine.py
import os
import json
import wave
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import speech_recognition as sr
import numpy as np
from agentics import LLM, system_message, user_message, assistant_message
from src.utils.logger import logger
from src.utils.config import settings


class TranscriptionEngine:
    """Motor de transcripción mejorado con capacidades de IA"""
    
    # En el __init__ de TranscriptionEngine, cambiar:

    def __init__(self, use_ai_enhancement: Optional[bool] = None):
        self.recognizer = sr.Recognizer()
        self.language = settings.transcription.language
        
        # Usar configuración del archivo .env si no se especifica
        if use_ai_enhancement is None:
            use_ai_enhancement = settings.use_ai_enhancement
        
        self.use_ai_enhancement = use_ai_enhancement
        
        # Inicializar LLM si está habilitado y hay API key
        if self.use_ai_enhancement and settings.openai_api_key:
            try:
                # Configurar la API key de OpenAI
                os.environ["OPENAI_API_KEY"] = settings.openai_api_key
                
                self.llm = LLM(
                    model=settings.ai_model,
                    temperature=0.3
                )
                logger.info(f"LLM inicializado: {settings.ai_model}")
            except Exception as e:
                logger.warning(f"No se pudo inicializar LLM: {e}")
                self.use_ai_enhancement = False
                self.llm = None
        else:
            self.llm = None
            if self.use_ai_enhancement and not settings.openai_api_key:
                logger.info("AI enhancement solicitado pero no hay API key configurada")
        
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribir un archivo de audio"""
        logger.info(f"Transcribiendo: {audio_path}")
        
        try:
            # Cargar y transcribir audio
            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
            
            # Intentar transcribir con Google Speech Recognition
            try:
                text = self.recognizer.recognize_google(
                    audio, 
                    language=self.language
                )
                confidence = 0.9
                
                # Mejorar transcripción con IA si está habilitado
                if self.use_ai_enhancement and self.llm and text:
                    text = await self._enhance_transcription(text)
                
            except sr.UnknownValueError:
                text = "[Inaudible]"
                confidence = 0.0
                
            except sr.RequestError as e:
                logger.error(f"Error en servicio de reconocimiento: {e}")
                text = "[Error de transcripción]"
                confidence = 0.0
                
            result = {
                "text": text,
                "confidence": confidence,
                "language": self.language,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Identificar hablante
            if settings.transcription.enable_speaker_identification:
                audio_features = self._extract_audio_features(audio_path)
                speaker = await self._identify_speaker(audio_features, text)
                result["speaker"] = speaker
            
            # Guardar en cache
            self.transcription_cache[audio_path] = result
            
            return result
                
        except Exception as e:
            logger.error(f"Error transcribiendo audio: {e}")
            return {
                "text": "[Error]",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _enhance_transcription(self, text: str) -> str:
        """Mejorar transcripción usando LLM"""
        try:
            messages = [
                system_message(
                    "Eres un asistente que mejora transcripciones de audio. "
                    "Corrige errores gramaticales y de puntuación manteniendo el significado original. "
                    "No agregues información que no esté en el texto original."
                ),
                user_message(
                    f"Mejora esta transcripción manteniendo el contenido original:\n\n{text}"
                )
            ]
            
            response = await self.llm.async_generate(messages)
            enhanced_text = response.content.strip()
            
            logger.debug(f"Transcripción mejorada: {text} -> {enhanced_text}")
            return enhanced_text
            
        except Exception as e:
            logger.warning(f"No se pudo mejorar transcripción: {e}")
            return text
    
    async def _identify_speaker(self, audio_features: Dict[str, Any], text: str) -> str:
        """Identificar hablante usando características de audio y contexto"""
        energy = audio_features.get("energy", 0)
        
        # Si tenemos LLM, usar para análisis contextual
        if self.use_ai_enhancement and self.llm and text and text != "[Inaudible]":
            try:
                # Analizar estilo de habla para identificar hablante
                messages = [
                    system_message(
                        "Analiza el estilo de habla y determina si es formal o informal, "
                        "técnico o casual. Responde solo con: FORMAL, INFORMAL, TECNICO o CASUAL"
                    ),
                    user_message(f"Texto: {text}")
                ]
                
                response = await self.llm.async_generate(messages)
                style = response.content.strip().upper()
                
                # Asignar hablante basado en estilo y energía
                if style in ["FORMAL", "TECNICO"]:
                    speaker = "Presentador" if energy > 0.5 else "Moderador"
                else:
                    speaker = f"Participante {int(energy * 3) + 1}"
                    
            except Exception as e:
                logger.debug(f"Error en análisis de hablante: {e}")
                speaker = self._simple_speaker_identification(energy)
        else:
            speaker = self._simple_speaker_identification(energy)
            
        return speaker
    
    def _simple_speaker_identification(self, energy: float) -> str:
        """Identificación simple de hablante basada en energía"""
        if energy < 0.3:
            return "Hablante 1"
        elif energy < 0.6:
            return "Hablante 2"
        else:
            return "Hablante 3"
    
    def _extract_audio_features(self, audio_path: str) -> Dict[str, float]:
        """Extraer características del audio"""
        try:
            with wave.open(audio_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # Calcular características
                energy = np.sqrt(np.mean(audio_data**2)) / 32768.0
                
                # Calcular pitch dominante (frecuencia fundamental aproximada)
                # Usando autocorrelación simple
                autocorr = np.correlate(audio_data, audio_data, mode='full')
                autocorr = autocorr[len(autocorr)//2:]
                
                # Encontrar primer pico después del origen
                first_peak = np.argmax(autocorr[20:500]) + 20
                pitch = wav_file.getframerate() / first_peak if first_peak > 0 else 0
                
                return {
                    "energy": float(energy),
                    "pitch": float(pitch),
                    "duration": wav_file.getnframes() / wav_file.getframerate()
                }
        except Exception as e:
            logger.error(f"Error extrayendo características: {e}")
            return {"energy": 0.0, "pitch": 0.0, "duration": 0.0}
    
    async def generate_meeting_summary(self, transcriptions: List[Dict[str, Any]]) -> str:
        """Generar resumen de la reunión usando IA"""
        if not self.use_ai_enhancement or not self.llm:
            return "Resumen no disponible (IA no habilitada)"
        
        try:
            # Combinar todas las transcripciones
            full_text = "\n".join([
                f"{t.get('speaker', 'Desconocido')}: {t.get('text', '')}"
                for t in transcriptions
                if t.get('text') and t.get('text') != "[Inaudible]"
            ])
            
            if not full_text:
                return "No hay suficiente contenido para generar un resumen"
            
            messages = [
                system_message(
                    "Genera un resumen conciso de esta reunión. "
                    "Incluye los puntos principales discutidos y cualquier decisión tomada."
                ),
                user_message(f"Transcripción de la reunión:\n\n{full_text}")
            ]
            
            response = await self.llm.async_generate(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return "Error al generar resumen"
    
    def format_transcription(self, transcriptions: List[Dict[str, Any]]) -> str:
        """Formatear transcripciones para salida"""
        output = []
        output.append("=== TRANSCRIPCIÓN DE REUNIÓN ===")
        output.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d')}")
        output.append(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
        output.append(f"Duración: {len(transcriptions) * 5} segundos aprox.")
        
        # Contar participantes únicos
        speakers = set(t.get("speaker", "Desconocido") for t in transcriptions)
        output.append(f"Participantes detectados: {len(speakers)}")
        
        output.append("\n=== CONTENIDO ===")
        
        for i, trans in enumerate(transcriptions):
            timestamp = f"{i * 5:02d}:{(i * 5) % 60:02d}"
            speaker = trans.get("speaker", "Desconocido")
            text = trans.get("text", "")
            
            if text and text not in ["[Inaudible]", "[Error]"]:
                output.append(f"[{timestamp}] {speaker}: {text}")
        
        output.append("\n=== ESTADÍSTICAS ===")
        
        # Estadísticas
        valid_transcriptions = [t for t in transcriptions if t.get("text") not in ["[Inaudible]", "[Error]", None]]
        output.append(f"Total de segmentos: {len(transcriptions)}")
        output.append(f"Segmentos transcritos: {len(valid_transcriptions)}")
        
        # Contar palabras
        total_words = sum(len(t.get("text", "").split()) for t in valid_transcriptions)
        output.append(f"Total de palabras: {total_words}")
        
        # Promedio de confianza
        confidences = [t.get("confidence", 0) for t in valid_transcriptions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        output.append(f"Confianza promedio: {avg_confidence:.1%}")
        
        return "\n".join(output)
    