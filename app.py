import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from sqlalchemy.orm import Session
from datetime import datetime
import os
from auth import authenticate_user, hash_password
from db import SessionLocal
from models import User, Employee, AppRole, Department
from permissions import can_view_employee, get_managers_and_departments
from work_time import start_workday, end_workday
from backup import create_backup, export_employees_to_csv, create_full_sql_backup, upload_to_yandex_disk
from settings import settings as app_settings

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HR-система - Вход")
        self.geometry("800x400")
        self.session: Session = SessionLocal()
        self.user: User | None = None

        tk.Label(self, text="Логин:").pack(pady=5)
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        tk.Label(self, text="Пароль:").pack(pady=5)
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        tk.Button(self, text="Войти", command=self.on_login).pack(pady=10)

    def on_login(self):
        login = self.username_entry.get()
        password = self.password_entry.get()

        if not login or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return
        user = authenticate_user(login, password, session=self.session)

        if user is None:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            return

        self.user = user
        self.destroy()
        main_window = MainWindow(self.session, self.user)
        main_window.mainloop()



class MainWindow(tk.Tk):
    def __init__(self, session: Session, user: User):
        super().__init__()
        self.session = session
        self.user = user
        self.title(f"HR-система - {user.username} ({user.role.value})")
        self.geometry("900x650")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.employee_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.employee_tab, text="Моя информация")

        self.build_employee_tab()

        if user.role == AppRole.MANAGER:
            self.dept_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.dept_tab, text="Сотрудники отдела")
            self.build_department_tab()

        if user.role == AppRole.GENERAL_DIRECTOR:
            self.gd_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.gd_tab, text="Менеджеры и отделы")
            self.build_gd_tab()

        if user.role in (AppRole.ADMIN, AppRole.HR):
            self.backup_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.backup_tab, text="Бэкапы и выгрузки")
            self.build_backup_tab()
            self.hr_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.hr_tab, text="Сотрудники (HR)")
            self.build_hr_tab()

    def build_employee_tab(self):
        employee: Employee | None = self.user.employee
        if not employee:
            tk.Label(self.employee_tab, text="Нет связанной записи сотрудника.").pack()
            return

        info = [
            f"ID: {employee.id}",
            f"ФИО: {employee.full_name}",
            f"Должность: {employee.position or ''}",
            f"Отдел: {employee.department.name if employee.department else ''}",
        ]
        for line in info:
            tk.Label(self.employee_tab, text=line, anchor="w").pack(fill=tk.X, padx=10, pady=2)
        btn_frame = tk.Frame(self.employee_tab)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Начать день", command=self.on_start_day).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Закончить день", command=self.on_end_day).grid(row=0, column=1, padx=5)
        self.logs_tree = ttk.Treeview(
            self.employee_tab,
            columns=("date", "start", "end", "hours"),
            show="headings",
        )
        self.logs_tree.heading("date", text="Дата")
        self.logs_tree.heading("start", text="Начало")
        self.logs_tree.heading("end", text="Конец")
        self.logs_tree.heading("hours", text="Часы")
        self.logs_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.refresh_logs()

    def refresh_logs(self):
        employee: Employee | None = self.user.employee
        for row in self.logs_tree.get_children():
            self.logs_tree.delete(row)
        if not employee:
            return
        logs = employee.work_logs
        for log in logs:
            date_str = log.date.strftime("%Y-%m-%d") if log.date else ""
            start_str = log.start_time.strftime("%H:%M") if log.start_time else ""
            end_str = log.end_time.strftime("%H:%M") if log.end_time else ""
            hours_str = f"{log.worked_hours:.2f}" if log.worked_hours is not None else ""
            self.logs_tree.insert("", tk.END, values=(date_str, start_str, end_str, hours_str))

    def on_start_day(self):
        msg = start_workday(self.session, self.user.employee)
        messagebox.showinfo("Информация", msg)
        self.refresh_logs()

    def on_end_day(self):
        msg = end_workday(self.session, self.user.employee)
        messagebox.showinfo("Информация", msg)
        self.refresh_logs()

    def build_department_tab(self):
        employee: Employee | None = self.user.employee
        if not employee or not employee.department:
            tk.Label(self.dept_tab, text="У вас не назначен отдел.").pack()
            return

        dept = employee.department
        tk.Label(self.dept_tab, text=f"Отдел: {dept.name}", font=("Arial", 12, "bold")).pack(pady=5)

        self.dept_tree = ttk.Treeview(
            self.dept_tab,
            columns=("id", "name", "position"),
            show="headings",
        )
        self.dept_tree.heading("id", text="ID")
        self.dept_tree.heading("name", text="ФИО")
        self.dept_tree.heading("position", text="Должность")
        self.dept_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for emp in dept.employees:
            if can_view_employee(self.user, emp):
                self.dept_tree.insert("", tk.END, values=(emp.id, emp.full_name, emp.position or ""))

    def build_gd_tab(self):
        managers = get_managers_and_departments(self.session)
        tree = ttk.Treeview(
            self.gd_tab,
            columns=("manager", "department"),
            show="headings",
        )
        tree.heading("manager", text="Менеджер")
        tree.heading("department", text="Отдел")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for m in managers:
            dept_name = m.department.name if m.department else "-"
            tree.insert("", tk.END, values=(m.full_name, dept_name))

    def on_full_sql_backup_to_yandex(self):
        try:
            local_path = create_full_sql_backup()
            remote_path = upload_to_yandex_disk(local_path)
            msg = (
                f"Полный SQL-бэкап PostgreSQL создан:\n{local_path}\n\n"
                f"Загружен на Яндекс.Диск:\n{remote_path}"
            )
            messagebox.showinfo("Полный бэкап PostgreSQL", msg)
            self.log_backup_message(msg)
        except Exception as exc:
            err_msg = f"Ошибка полного бэкапа PostgreSQL: {exc}"
            messagebox.showerror("Ошибка полного бэкапа PostgreSQL", err_msg)
            self.log_backup_message(err_msg)

    def build_backup_tab(self):
        frame = self.backup_tab

        tk.Label(
            frame,
            text="Резервные копии и выгрузки",
            font=("Arial", 12, "bold"),
        ).pack(pady=5)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=10, padx=10, anchor="w")

        tk.Button(
            btn_frame,
            text="Создать JSON-бэкап",
            command=self.on_create_backup,
            width=25,
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            btn_frame,
            text="Создать JSON-бэкап и отправить на SFTP",
            command=lambda: self.on_create_backup(upload_sftp=True),
            width=35,
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            btn_frame,
            text="Экспорт сотрудников в CSV",
            command=self.on_export_employees,
            width=25,
        ).grid(row=1, column=0, padx=5, pady=5)

        tk.Button(
            btn_frame,
            text="Полный SQL-бэкап PostgreSQL и отправка на Яндекс.Диск",
            command=self.on_full_sql_backup_to_yandex,
            width=45,
        ).grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        self.backup_log = tk.Text(frame, height=10, state="disabled")
        self.backup_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def log_backup_message(self, text: str):
        self.backup_log.configure(state="normal")
        self.backup_log.insert(tk.END, text + "\n")
        self.backup_log.see(tk.END)
        self.backup_log.configure(state="disabled")

    def on_create_backup(self, upload_sftp: bool = False):
        try:
            local_path, remote_path = create_backup(self.session, upload_sftp=upload_sftp)
            msg = f"Бэкап создан: {local_path}"
            if remote_path:
                msg += f"\nЗагружен на SFTP: {remote_path}"
            messagebox.showinfo("Бэкап", msg)
            self.log_backup_message(msg)
        except Exception as exc:
            messagebox.showerror("Ошибка бэкапа", str(exc))
            self.log_backup_message(f"Ошибка бэкапа: {exc!r}")

    def on_export_employees(self):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"employees_{ts}.csv"
        out_dir = app_settings.BACKUP_DIR
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, filename)
        try:
            export_employees_to_csv(self.session, path)
            messagebox.showinfo("Экспорт", f"Файл сохранён: {path}")
            self.log_backup_message(f"Экспорт в CSV: {path}")
        except Exception as exc:
            messagebox.showerror("Ошибка экспорта", str(exc))
            self.log_backup_message(f"Ошибка экспорта сотрудников: {exc!r}")

    def build_hr_tab(self):
        form_frame = tk.LabelFrame(self.hr_tab, text="Добавить сотрудника")
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(form_frame, text="ФИО:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.hr_fullname_entry = tk.Entry(form_frame, width=40)
        self.hr_fullname_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        tk.Label(form_frame, text="Должность:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.hr_position_entry = tk.Entry(form_frame, width=40)
        self.hr_position_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        tk.Label(form_frame, text="Отдел:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.hr_department_combo = ttk.Combobox(form_frame, state="readonly", width=37)
        self.hr_department_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        departments = self.session.query(Department).order_by(Department.name).all()
        self.hr_departments_by_name = {d.name: d.id for d in departments}
        self.hr_department_combo["values"] = list(self.hr_departments_by_name.keys())

        user_frame = tk.LabelFrame(self.hr_tab, text="Учетная запись (User)")
        user_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(user_frame, text="Логин:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.hr_username_entry = tk.Entry(user_frame, width=30)
        self.hr_username_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        tk.Label(user_frame, text="Пароль:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.hr_password_entry = tk.Entry(user_frame, width=30, show="*")
        self.hr_password_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        tk.Label(user_frame, text="Роль:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.hr_role_combo = ttk.Combobox(user_frame, state="readonly", width=27)
        self.hr_role_combo["values"] = [
            AppRole.EMPLOYEE.value,
            AppRole.MANAGER.value,
        ]
        self.hr_role_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        self.hr_role_combo.set(AppRole.EMPLOYEE.value)

        tk.Button(
            form_frame,
            text="Добавить сотрудника и пользователя",
            command=self.on_hr_add_employee,
        ).grid(row=3, column=0, columnspan=2, pady=10)

        add_dept_btn = tk.Button(
            form_frame,
            text="Добавить отдел",
            command=self.on_hr_add_department,
        )
        add_dept_btn.grid(row=2, column=2, sticky="w", padx=5, pady=5)
        list_frame = tk.LabelFrame(self.hr_tab, text="Сотрудники")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.hr_tree = ttk.Treeview(
            list_frame,
            columns=("id", "name", "position", "department"),
            show="headings",
        )
        self.hr_tree.heading("id", text="ID")
        self.hr_tree.heading("name", text="ФИО")
        self.hr_tree.heading("position", text="Должность")
        self.hr_tree.heading("department", text="Отдел")
        self.hr_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.refresh_hr_departments()
        self.refresh_hr_employees()

    def on_hr_add_employee(self):
        full_name = self.hr_fullname_entry.get().strip()
        position = self.hr_position_entry.get().strip()
        dept_name = self.hr_department_combo.get().strip()

        username = self.hr_username_entry.get().strip()
        password = self.hr_password_entry.get().strip()
        role_value = self.hr_role_combo.get().strip()
        if not full_name:
            messagebox.showerror("Ошибка", "ФИО обязательно для заполнения")
            return
        if not username:
            messagebox.showerror("Ошибка", "Логин обязателен для создания пользователя")
            return
        if not password:
            messagebox.showerror("Ошибка", "Пароль обязателен для создания пользователя")
            return
        if not role_value:
            messagebox.showerror("Ошибка", "Роль пользователя не выбрана")
            return
        dept_id = None
        if dept_name:
            dept_id = self.hr_departments_by_name.get(dept_name)
            if dept_id is None:
                messagebox.showerror("Ошибка", f"Выбран несуществующий отдел: '{dept_name}'")
                return

        try:
            existing_user = (
                self.session.query(User)
                .filter(User.username == username)
                .one_or_none()
            )
            if existing_user is not None:
                messagebox.showerror("Ошибка", f"Пользователь с логином '{username}' уже существует")
                return
            try:
                role = AppRole(role_value)
            except ValueError:
                messagebox.showerror("Ошибка", f"Неверное значение роли: '{role_value}'")
                return
            new_emp = Employee(
                full_name=full_name,
                position=position or None,
                department_id=dept_id,
            )
            self.session.add(new_emp)
            hashed = hash_password(password)
            new_user = User(
                username=username,
                password_hash=hashed,
                role=role,
                employee=new_emp,
            )
            self.session.add(new_user)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            print("Ошибка при добавлении сотрудника:", exc)
            messagebox.showerror("Ошибка", f"Не удалось добавить сотрудника/пользователя: {exc}")
            return
        messagebox.showinfo(
            "",
            f"Сотрудник '{full_name}' и пользователь '{username}' добавлены",
        )
        self.hr_fullname_entry.delete(0, tk.END)
        self.hr_position_entry.delete(0, tk.END)
        self.hr_username_entry.delete(0, tk.END)
        self.hr_password_entry.delete(0, tk.END)
        self.hr_role_combo.set(AppRole.EMPLOYEE.value)
        self.hr_department_combo.set("")
        self.refresh_hr_employees()

    def refresh_hr_employees(self):
        for row_id in self.hr_tree.get_children():
            self.hr_tree.delete(row_id)
        employees = (
            self.session.query(Employee)
            .outerjoin(Department)
            .order_by(Employee.full_name)
            .all()
        )

        for emp in employees:
            dept_name = emp.department.name if emp.department else ""
            self.hr_tree.insert(
                "",
                "end",
                values=(
                    emp.id,
                    emp.full_name,
                    emp.position or "",
                    dept_name,
                ),
            )

    def on_hr_add_department(self):
        name = simpledialog.askstring("Новый отдел", "Введите название отдела:")
        if not name:
            return
        name = name.strip()
        if not name:
            return
        existing = (
            self.session.query(Department)
            .filter(Department.name == name)
            .one_or_none()
        )
        if existing is not None:
            messagebox.showerror("Ошибка", f"Отдел с названием '{name}' уже существует")
            return

        try:
            new_dept = Department(name=name)
            self.session.add(new_dept)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            messagebox.showerror("Ошибка", f"Не удалось добавить отдел: {exc}")
            return
        messagebox.showinfo("", f"Отдел '{name}' добавлен")
        self.refresh_hr_departments()

    def refresh_hr_departments(self):
        departments = (
            self.session.query(Department)
            .order_by(Department.name)
            .all()
        )
        self.hr_departments_by_name = {d.name: d.id for d in departments}
        self.hr_department_combo["values"] = list(self.hr_departments_by_name.keys())