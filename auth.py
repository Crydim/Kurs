from getpass import getpass

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from models import User, AppRole
from settings import settings
from db import SessionLocal


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.verify(password, hashed)


def ensure_admin_exists() -> None:
    with SessionLocal() as session:
        admin = session.query(User).filter_by(username=settings.ADMIN_DEFAULT_LOGIN).first()
        if not admin:
            admin = User(
                username=settings.ADMIN_DEFAULT_LOGIN,
                password_hash=hash_password(settings.ADMIN_DEFAULT_PASSWORD),
                role=AppRole.ADMIN,
            )
            session.add(admin)
            session.commit()


def login(session: Session) -> User | None:
    username = input("Логин: ").strip()
    password = getpass("Пароль: ")

    user = session.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        print("Неверный логин или пароль.")
        return None
    return user


def require_role(user: User, allowed: list[AppRole]) -> bool:
    if user.role in allowed:
        return True
    print("Недостаточно прав для выполнения операции.")
    return False