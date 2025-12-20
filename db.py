from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from settings import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DB_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from models import (  # noqa: F401
        User,
        AccessLevel,
        Owner,
        GeneralDirector,
        Department,
        DepartmentManager,
        Employee,
        Profile,
        ContactInfo,
        EmploymentContract,
        WorkStatus,
        WorkLog,
        DismissalReason,
        Dismissal,
    )

    Base.metadata.create_all(bind=engine)