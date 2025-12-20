from db import init_db
from backup import create_full_sql_backup, upload_to_yandex_disk


def run_daily_full_backup():
    try:
        init_db()
    except Exception:
        pass

    local_path = create_full_sql_backup()
    print(f"Локальный бэкап создан: {local_path}")

    remote_path = upload_to_yandex_disk(local_path)
    print(f"Бэкап загружен на Яндекс.Диск: {remote_path}")

if __name__ == "__main__":
    run_daily_full_backup()