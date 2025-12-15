from getpass import getpass

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from models import User, AppRole
from settings import settings
from db import SessionLocal


def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.verify(plain_password, hashed_password)

def authenticate_user(login: str, password: str, session: Session | None = None) -> User | None:
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        user = session.query(User).filter(User.username == login).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    finally:
        if close_session:
            session.close()

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