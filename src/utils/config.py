# src/utils/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import json
from pathlib import Path


class AudioSettings(BaseSettings):
    sample_rate: int = 16000
    channels: int = 1
    buffer_size: int = 1024
    device_index: Optional[int] = None


class TranscriptionSettings(BaseSettings):
    language: str = "es-ES"
    interval_seconds: int = 5
    enable_speaker_identification: bool = True


class AutomationSettings(BaseSettings):
    wait_timeout: int = 30
    headless_mode: bool = False
    auto_join: bool = True
    retry_attempts: int = 3


class OutputSettings(BaseSettings):
    format: str = "txt"
    include_timestamps: bool = True
    include_statistics: bool = True
    encryption_enabled: bool = False


class Settings(BaseSettings):
    # App settings
    app_name: str = "Meet Transcription Bot"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API settings
    api_host: str = Field(default="127.0.0.1", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Database
    database_url: str = Field(default="sqlite:///./meet_transcriptions.db", env="DATABASE_URL")
    
    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")

    # Agregar estas líneas a la clase Settings en src/utils/config.py:

    # AI settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    use_ai_enhancement: bool = Field(default=False, env="USE_AI_ENHANCEMENT")
    ai_model: str = Field(default="gpt-4.1-nano", env="AI_MODEL")
    
    # Sub-settings
    audio: AudioSettings = AudioSettings()
    transcription: TranscriptionSettings = TranscriptionSettings()
    automation: AutomationSettings = AutomationSettings()
    output: OutputSettings = OutputSettings()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Permitir campos extra
    
    def load_from_json(self, config_path: str = "config/settings.json"):
        """Cargar configuración desde archivo JSON"""
        path = Path(config_path)
        if path.exists():
            with open(path, 'r') as f:
                config_data = json.load(f)
                
            # Actualizar configuraciones
            if 'audio' in config_data:
                self.audio = AudioSettings(**config_data['audio'])
            if 'transcription' in config_data:
                self.transcription = TranscriptionSettings(**config_data['transcription'])
            if 'automation' in config_data:
                self.automation = AutomationSettings(**config_data['automation'])
            if 'output' in config_data:
                self.output = OutputSettings(**config_data['output'])


# Instancia global de configuración
settings = Settings()
settings.load_from_json()
