from datetime import datetime, date
from sqlalchemy.orm import Session

from models import Employee, WorkLog, WorkStatus


def get_or_create_today_log(session: Session, employee: Employee) -> WorkLog:
    today = date.today()
    log = (
        session.query(WorkLog)
        .filter(
            WorkLog.employee_id == employee.id,
            WorkLog.date >= datetime(today.year, today.month, today.day),
        )
        .order_by(WorkLog.date.desc())
        .first()
    )
    if log is None:
        log = WorkLog(employee_id=employee.id, date=datetime.utcnow())
        session.add(log)
        session.flush()
    return log


def start_workday(session: Session, employee: Employee) -> str:
    log = get_or_create_today_log(session, employee)
    if log.start_time is not None:
        return "Рабочий день уже начат."
    log.start_time = datetime.utcnow()

    if employee.status is None:
        status = WorkStatus(
            employee_id=employee.id,
            current_status="working",
            workday_start=log.start_time.time(),
        )
        session.add(status)
    else:
        employee.status.current_status = "working"
        employee.status.workday_start = log.start_time.time()
    session.commit()
    return "Начало рабочего дня зафиксировано."


def end_workday(session: Session, employee: Employee) -> str:
    log = get_or_create_today_log(session, employee)
    if log.start_time is None:
        return "Нельзя завершить день: начало ещё не зафиксировано."
    if log.end_time is not None:
        return "Рабочий день уже завершён."

    log.end_time = datetime.utcnow()
    delta = log.end_time - log.start_time
    log.worked_hours = round(delta.total_seconds() / 3600, 2)

    if employee.status:
        employee.status.current_status = "off"
        employee.status.workday_end = log.end_time.time()
        employee.status.current_hours = log.worked_hours or 0.0

    session.commit()
    return f"Конец рабочего дня зафиксирован. Отработано часов: {log.worked_hours}"