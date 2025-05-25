import sys
import os
from datetime import datetime

# Tambahkan path root project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Device, Pelanggaran, Gambar, Keamanan

app = create_app()

with app.app_context():
    print("🚀 Menjalankan seeder...")

    # Bersihkan isi semua tabel dulu (opsional)
    Keamanan.query.delete()
    Gambar.query.delete()
    Pelanggaran.query.delete()
    Device.query.delete()
    db.session.commit()

    # ===== Tambah Device =====
    d1 = Device(nama="Raspbery-PI")
    d2 = Device(nama="ESP-32 CAM")
    db.session.add_all([d1, d2])
    db.session.commit()
    print("✅ Device berhasil ditambahkan.")

    # ===== Tambah Pelanggaran =====
    p1 = Pelanggaran(
        waktu=datetime(2025, 5, 25, 10, 30),
        plat_nomor="B1234XYZ",
        confidence=89.5,
        device_id=d1.id
    )

    p2 = Pelanggaran(
        waktu=datetime(2025, 5, 25, 10, 35),
        plat_nomor="D5678ABC",
        confidence=92.3,
        device_id=d2.id
    )
    db.session.add_all([p1, p2])
    db.session.commit()
    print("✅ Pelanggaran berhasil ditambahkan.")

    # ===== Tambah Gambar =====
    g1 = Gambar(
        nama_file="b1234xyz.jpg",
        tipe="crop",
        resolusi="400x130",
        ukuran_byte=5000,
        ukuran_terenkripsi=5100,
        pelanggaran_id=p1.id
    )
    g2 = Gambar(
        nama_file="d5678abc.jpg",
        tipe="crop",
        resolusi="400x130",
        ukuran_byte=5200,
        ukuran_terenkripsi=5300,
        pelanggaran_id=p2.id
    )
    db.session.add_all([g1, g2])
    db.session.commit()
    print("✅ Gambar berhasil ditambahkan.")

    # ===== Tambah Keamanan =====
    k1 = Keamanan(
        pelanggaran_id=p1.id,
        nonce="abc123nonce",
        ciphertext_len=1234,
        poly1305_tag="tag123",
        poly1305_valid=True,
        encrypt_time_ms=12.5,
        decrypt_time_ms=10.2,
        total_process_ms=25.0,
        gambar_valid=True,
        delivery_status="Seeded"
    )
    k2 = Keamanan(
        pelanggaran_id=p2.id,
        nonce="xyz789nonce",
        ciphertext_len=1357,
        poly1305_tag="tag789",
        poly1305_valid=True,
        encrypt_time_ms=13.8,
        decrypt_time_ms=9.7,
        total_process_ms=23.5,
        gambar_valid=True,
        delivery_status="Seeded"
    )
    db.session.add_all([k1, k2])
    db.session.commit()
    print("✅ Keamanan berhasil ditambahkan.")

    print("🎉 Seeder selesai.")
