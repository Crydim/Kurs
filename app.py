import tkinter as tk
from tkinter import ttk, messagebox

from sqlalchemy.orm import Session

from auth import authenticate_user
from db import SessionLocal
from models import User, Employee, AppRole
from permissions import can_view_employee, get_managers_and_departments
from work_time import start_workday, end_workday
from backup import create_backup, export_employees_to_csv


class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HR-система - Вход")
        self.geometry("300x150")
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
        from datetime import datetime
        import os

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"employees_{ts}.csv"
        from settings import settings as app_settings

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