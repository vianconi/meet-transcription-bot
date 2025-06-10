# src/database.py
from sqlmodel import create_engine, SQLModel, Session
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# Obtener URL de la base de datos desde variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meet_transcriptions.db")

# Crear engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)


def create_db_and_tables():
    """Crear todas las tablas en la base de datos"""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    """Context manager para manejar sesiones de base de datos"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """Dependency para FastAPI"""
    with Session(engine) as session:
        yield session
        