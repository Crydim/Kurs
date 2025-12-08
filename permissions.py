from sqlalchemy.orm import Session

from models import User, AppRole, Employee, DepartmentManager, Department, GeneralDirector


def get_employee_for_user(session: Session, user: User) -> Employee | None:
    return user.employee


def can_view_employee(user: User, target_employee: Employee) -> bool:
    if user.role in (AppRole.ADMIN, AppRole.HR):
        return True

    if user.role == AppRole.EMPLOYEE:
        return user.employee_id == target_employee.id

    if user.role == AppRole.MANAGER:
        if user.employee_id == target_employee.id:
            return True
        if not user.employee or not user.employee.department:
            return False
        return target_employee.department_id == user.employee.department_id

    if user.role == AppRole.GENERAL_DIRECTOR:
        return True

    if user.role == AppRole.VIEWER:
        return False

    return False


def get_managers_and_departments(session: Session):
    return (
        session.query(DepartmentManager)
        .join(Department, Department.manager_id == DepartmentManager.id)
        .all()
    )