from app import create_app, db
from flask_migrate import upgrade, migrate, init
import os
import shutil
from sqlalchemy import text
from sqlalchemy.engine import create_engine

# Buat app dulu
app = create_app()

def reset_mysql():
    # Ambil URI dari app.config langsung
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    engine = create_engine(uri.rsplit("/", 1)[0])  # koneksi ke root (tanpa nama DB)
    db_name = uri.rsplit("/", 1)[-1]

    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        conn.execute(text(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))

    print(f"✅ Database '{db_name}' dropped & recreated.")

def clean_migrations():
    if os.path.exists("migrations"):
        shutil.rmtree("migrations")
        print("🧹 Folder migrations dihapus.")

# Jalankan semua dalam konteks app Flask
with app.app_context():
    reset_mysql()
    clean_migrations()

    init()
    migrate(message="fresh migration")
    upgrade()
    print("🚀 Migrasi fresh selesai.")
