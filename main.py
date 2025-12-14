from db import init_db
from auth import ensure_admin_exists
from app import LoginWindow


def run():
    init_db()
    ensure_admin_exists()
    app = LoginWindow()
    app.mainloop()


if __name__ == "__main__":
    run()