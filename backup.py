import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable
import csv
from sqlalchemy.orm import Session
import subprocess
import requests

from settings import settings
from models import (
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


def _default_serializer(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "value"):  # Enum
        return obj.value
    return str(obj)


def _model_to_dict(obj) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for col in obj.__table__.columns:
        data[col.name] = getattr(obj, col.name)
    return data


def export_all_to_json(session: Session, output_path: str) -> None:
    export_map: Dict[str, Iterable[Any]] = {
        "users": session.query(User).all(),
        "access_levels": session.query(AccessLevel).all(),
        "owners": session.query(Owner).all(),
        "general_directors": session.query(GeneralDirector).all(),
        "departments": session.query(Department).all(),
        "department_managers": session.query(DepartmentManager).all(),
        "employees": session.query(Employee).all(),
        "profiles": session.query(Profile).all(),
        "contact_infos": session.query(ContactInfo).all(),
        "employment_contracts": session.query(EmploymentContract).all(),
        "work_statuses": session.query(WorkStatus).all(),
        "work_logs": session.query(WorkLog).all(),
        "dismissal_reasons": session.query(DismissalReason).all(),
        "dismissals": session.query(Dismissal).all(),
    }

    result: Dict[str, Any] = {}
    for name, objects in export_map.items():
        result[name] = [_model_to_dict(o) for o in objects]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=_default_serializer)


def export_employees_to_csv(session: Session, output_dir: str) -> None:

    os.makedirs(output_dir or ".", exist_ok=True)

    export_map: Dict[str, Iterable[Any]] = {
        "users": session.query(User).all(),
        "access_levels": session.query(AccessLevel).all(),
        "owners": session.query(Owner).all(),
        "general_directors": session.query(GeneralDirector).all(),
        "departments": session.query(Department).all(),
        "department_managers": session.query(DepartmentManager).all(),
        "employees": session.query(Employee).all(),
        "profiles": session.query(Profile).all(),
        "contact_infos": session.query(ContactInfo).all(),
        "employment_contracts": session.query(EmploymentContract).all(),
        "work_statuses": session.query(WorkStatus).all(),
        "work_logs": session.query(WorkLog).all(),
        "dismissal_reasons": session.query(DismissalReason).all(),
        "dismissals": session.query(Dismissal).all(),
    }

    for name, objects in export_map.items():
        rows = [_model_to_dict(o) for o in objects]
        fieldnames = list(rows[0].keys()) if rows else [
            col.name for col in objects[0].__table__.columns  # type: ignore[index]
        ] if objects else []

        file_path = os.path.join(output_dir, f"{name}.csv")

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(fieldnames)
            for row in rows:
                writer.writerow([
                    _default_serializer(row.get(col)) for col in fieldnames
                ])



def _upload_via_sftp(local_path: str) -> str:
    if not settings.SFTP_HOST or not settings.SFTP_USER:
        raise RuntimeError("SFTP не настроен (проверьте переменные окружения SFTP_*).")

    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("Модуль paramiko не установлен, SFTP недоступен.") from exc

    transport = paramiko.Transport((settings.SFTP_HOST, settings.SFTP_PORT))
    transport.connect(username=settings.SFTP_USER, password=settings.SFTP_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        remote_dir = settings.SFTP_REMOTE_DIR or "."
        try:
            sftp.chdir(remote_dir)
        except IOError:
            parts = [p for p in remote_dir.split("/") if p]
            path = ""
            for part in parts:
                path = f"{path}/{part}" if path else part
                try:
                    sftp.mkdir(path)
                except IOError:
                    pass
            sftp.chdir(remote_dir)
        filename = os.path.basename(local_path)
        remote_path = f"{remote_dir.rstrip('/')}/{filename}"
        sftp.put(local_path, remote_path)
        return remote_path
    finally:
        sftp.close()
        transport.close()


def create_backup(session: Session, upload_sftp: bool = False) -> tuple[str, str | None]:
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(settings.BACKUP_DIR, f"backup_{ts}.json")
    export_all_to_json(session, local_path)

    remote_path: str | None = None
    if upload_sftp:
        remote_path = _upload_via_sftp(local_path)

    return local_path, remote_path

def create_full_sql_backup() -> str:
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"full_backup_{ts}.sql"
    backup_path = os.path.join(settings.BACKUP_DIR, backup_filename)
    cmd = [
        settings.PG_DUMP_PATH,
        "-h",
        settings.PG_HOST,
        "-p",
        str(settings.PG_PORT),
        "-U",
        settings.PG_USER,
        "-d",
        settings.PG_DBNAME,
        "-F",
        "p",  # plain text SQL
        "-f",
        backup_path,
    ]
    env = os.environ.copy()
    env["PGPASSWORD"] = settings.PG_PASSWORD
    result = subprocess.run(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass
        raise RuntimeError(
            f"Ошибка pg_dump (код {result.returncode}):\n{result.stderr}"
        )
    return backup_path

YANDEX_DISK_API_BASE = "https://cloud-api.yandex.net/v1/disk"


def upload_to_yandex_disk(local_path: str) -> str:
    token = settings.YANDEX_DISK_TOKEN
    if not token:
        raise RuntimeError("Не задан токен YANDEX_DISK_TOKEN в settings/.env")

    filename = os.path.basename(local_path)
    remote_path = f"{settings.YANDEX_DISK_FOLDER}/{filename}"

    params = {
        "path": remote_path,
        "overwrite": "true",
    }
    headers = {
        "Authorization": f"OAuth {token}",
    }
    resp = requests.get(
        f"{YANDEX_DISK_API_BASE}/resources/upload",
        params=params,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    upload_url = resp.json()["href"]

    with open(local_path, "rb") as f:
        put_resp = requests.put(upload_url, data=f, timeout=300)
    put_resp.raise_for_status()

    return remote_path