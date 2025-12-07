import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_URL: str = os.getenv("DB_URL", "sqlite:///hr.db")

    ADMIN_DEFAULT_LOGIN: str = os.getenv("ADMIN_LOGIN", "admin")
    ADMIN_DEFAULT_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")

    SFTP_HOST: str | None = os.getenv("SFTP_HOST")
    SFTP_PORT: int = int(os.getenv("SFTP_PORT", 22))
    SFTP_USER: str | None = os.getenv("SFTP_USER")
    SFTP_PASSWORD: str | None = os.getenv("SFTP_PASSWORD")
    SFTP_REMOTE_DIR: str | None = os.getenv("SFTP_REMOTE_DIR")

settings = Settings()