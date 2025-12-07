from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .settings import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(
    settings.DB_URL,
    echo=False,           # True для отладки
    future=True
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)