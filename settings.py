import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB_URL: str = os.getenv("DB_URL", "postgresql://postgres:Zero2025Mori@localhost")

    ADMIN_DEFAULT_LOGIN: str = os.getenv("ADMIN_LOGIN", "admin")
    ADMIN_DEFAULT_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")

    SFTP_HOST: str | None = os.getenv("SFTP_HOST")
    SFTP_PORT: int = int(os.getenv("SFTP_PORT", 22))
    SFTP_USER: str | None = os.getenv("SFTP_USER")
    SFTP_PASSWORD: str | None = os.getenv("SFTP_PASSWORD")
    SFTP_REMOTE_DIR: str | None = os.getenv("SFTP_REMOTE_DIR")
    YANDEX_DISK_TOKEN: str = "y0__xCJzpPUAxjYvDwg8KmD4BXo1gAlfoSR4fZ433mNr2eFAstB9g"
    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_USER: str = "postgres"
    YANDEX_DISK_FOLDER: str = "/hr_backups"
    PG_DBNAME: str = "postgres"
    PG_DUMP_PATH: str = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
    PG_PASSWORD: str = "Zero2025Mori"
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "backups")


settings = Settings()