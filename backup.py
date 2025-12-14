import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable
import csv
from sqlalchemy.orm import Session

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