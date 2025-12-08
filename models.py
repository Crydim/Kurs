from __future__ import annotations

from datetime import datetime, time
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Text,
    DateTime,
    Time,
    Float,
    Enum,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base
import enum


class AppRole(str, enum.Enum):
    ADMIN = "admin"
    HR = "hr"
    MANAGER = "manager"
    VIEWER = "viewer"
    EMPLOYEE = "employee"
    GENERAL_DIRECTOR = "general_director"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AppRole] = mapped_column(Enum(AppRole), default=AppRole.VIEWER)

    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)
    employee: Mapped[Optional["Employee"]] = relationship(back_populates="user", uselist=False)


class AccessLevel(Base):
    __tablename__ = "access_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text())


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_type: Mapped[Optional[str]] = mapped_column(String(100))
    access_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("access_levels.id"))

    access_level: Mapped[Optional[AccessLevel]] = relationship()


class GeneralDirector(Base):
    __tablename__ = "general_directors"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("access_levels.id"))
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("owners.id"))

    access_level: Mapped[Optional[AccessLevel]] = relationship()
    owner: Mapped[Optional[Owner]] = relationship()


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    efficiency: Mapped[Optional[float]] = mapped_column(Float)
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("department_managers.id"))

    manager: Mapped[Optional["DepartmentManager"]] = relationship(back_populates="department")
    employees: Mapped[List["Employee"]] = relationship(back_populates="department")


class DepartmentManager(Base):
    __tablename__ = "department_managers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("access_levels.id"))

    department: Mapped[Optional[Department]] = relationship(back_populates="manager", uselist=False)
    access_level: Mapped[Optional[AccessLevel]] = relationship()


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(255))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    access_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("access_levels.id"))

    department: Mapped[Optional[Department]] = relationship(back_populates="employees")
    access_level: Mapped[Optional[AccessLevel]] = relationship()

    profile: Mapped[Optional["Profile"]] = relationship(back_populates="employee", uselist=False)
    contract: Mapped[Optional["EmploymentContract"]] = relationship(back_populates="employee", uselist=False)
    status: Mapped[Optional["WorkStatus"]] = relationship(back_populates="employee", uselist=False)
    user: Mapped[Optional[User]] = relationship(back_populates="employee", uselist=False)
    dismissals: Mapped[List["Dismissal"]] = relationship(back_populates="employee")
    work_logs: Mapped[List["WorkLog"]] = relationship(back_populates="employee")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True)
    warnings_count: Mapped[int] = mapped_column(Integer, default=0)
    access_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("access_levels.id"))

    employee: Mapped[Employee] = relationship(back_populates="profile")
    access_level: Mapped[Optional[AccessLevel]] = relationship()
    contacts: Mapped[Optional["ContactInfo"]] = relationship(back_populates="profile", uselist=False)


class ContactInfo(Base):
    __tablename__ = "contact_infos"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(String(255))

    profile: Mapped[Profile] = relationship(back_populates="contacts")


class ContractStatus(str, enum.Enum):
    ACTIVE = "active"
    TERMINATED = "terminated"
    ON_HOLD = "on_hold"


class EmploymentContract(Base):
    __tablename__ = "employment_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True)
    access_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("access_levels.id"))

    content: Mapped[Optional[str]] = mapped_column(Text())
    salary: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[ContractStatus] = mapped_column(Enum(ContractStatus), default=ContractStatus.ACTIVE)

    employee: Mapped[Employee] = relationship(back_populates="contract")
    access_level: Mapped[Optional[AccessLevel]] = relationship()


class WorkStatus(Base):
    __tablename__ = "work_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True)

    current_status: Mapped[str] = mapped_column(String(50))
    workday_start: Mapped[Optional[time]] = mapped_column(Time)
    workday_end: Mapped[Optional[time]] = mapped_column(Time)
    breaks_taken: Mapped[int] = mapped_column(Integer, default=0)
    current_hours: Mapped[float] = mapped_column(Float, default=0)

    employee: Mapped[Employee] = relationship(back_populates="status")


class WorkLog(Base):
    __tablename__ = "work_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    worked_hours: Mapped[Optional[float]] = mapped_column(Float)

    employee: Mapped[Employee] = relationship(back_populates="work_logs")


class DismissalReason(Base):
    __tablename__ = "dismissal_reasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text())


class Dismissal(Base):
    __tablename__ = "dismissals"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    reason_id: Mapped[int] = mapped_column(ForeignKey("dismissal_reasons.id"))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    comment: Mapped[Optional[str]] = mapped_column(Text())

    employee: Mapped[Employee] = relationship(back_populates="dismissals")
    reason: Mapped[DismissalReason] = relationship()