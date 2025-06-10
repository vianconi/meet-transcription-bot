# src/utils/logger.py
import logging
import sys
from pathlib import Path
from datetime import datetime
from src.utils.config import settings


def setup_logger(name: str = "meet_transcription_bot") -> logging.Logger:
    """Configurar y retornar un logger"""
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Crear logger
    logger = logging.getLogger(name)
    
    # Usar log_level de settings si existe
    log_level = getattr(settings, 'log_level', 'INFO')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Handler para archivo
    log_file = getattr(settings, 'log_file', f"logs/{datetime.now().strftime('%Y%m%d')}_app.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Agregar handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Logger global
logger = setup_logger()
