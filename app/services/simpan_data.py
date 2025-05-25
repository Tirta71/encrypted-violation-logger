import base64
import os
import time
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from app import db
from app.models import Pelanggaran, Keamanan, Gambar

# === Kunci untuk dekripsi ===
KEY_B64 = "kKgTWK1FuLFlHrxRX8xlE7e9IYvqqMaI8CyZGhmmu6c="
KEY = base64.b64decode(KEY_B64)

# === Fungsi Dekripsi ===
def decrypt_chacha(nonce_b64, ciphertext_b64):
    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    chacha = ChaCha20Poly1305(KEY)

    start = time.perf_counter()
    plaintext = chacha.decrypt(nonce, ciphertext, None)
    decrypt_time = round((time.perf_counter() - start) * 1000, 2)  # ✅ dibulatkan 2 digit

    return plaintext, decrypt_time




# === Fungsi Simpan Data ===
def simpan_ke_database(payload):
    try:
        total_start = time.time()

        waktu_obj = datetime.fromisoformat(payload["timestamp"])
        nama_file = payload["gambar"]["nama_file"]

        # Cegah duplikat berdasarkan nama_file
        if Gambar.query.filter_by(nama_file=nama_file).first():
            print(f"⚠️ Duplikat terdeteksi, nama file '{nama_file}' sudah ada.")
            return

        # === Dekripsi OCR ===
        ocr_data = payload.get("ocr", {})
        ocr_plain, _ = decrypt_chacha(ocr_data["nonce"], ocr_data["ciphertext"])
        ocr_text = ocr_plain.decode("utf-8")
        poly1305_tag = ocr_data.get("poly1305_tag")
        encrypt_ocr_ms = ocr_data.get("encrypt_time_ms")

        # === Dekripsi dan simpan gambar ===
        gambar_data = payload.get("gambar", {})
        gambar_bytes, decrypt_img_ms = decrypt_chacha(gambar_data["nonce"], gambar_data["ciphertext"])
        print(f"🕒 Waktu dekripsi gambar: {decrypt_img_ms} ms")



        save_dir = os.path.join("static", "gambar_plat")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, gambar_data["nama_file"])
        with open(save_path, "wb") as f:
            f.write(gambar_bytes)

        # === Simpan Pelanggaran ===
        pelanggaran = Pelanggaran(
            waktu=waktu_obj,
            plat_nomor=payload["plat_nomor"],
            confidence=payload["confidence"],
            device_id=payload["device_id"]
        )
        db.session.add(pelanggaran)
        db.session.commit()

        # === Simpan Keamanan ===
        encrypt_img_ms = round(gambar_data.get("encrypt_time_ms", 0), 2)
        total_ms = round(encrypt_img_ms + decrypt_img_ms, 2)
        keamanan = Keamanan(
            pelanggaran_id=pelanggaran.id,
            nonce=ocr_data["nonce"],
            poly1305_tag=poly1305_tag,
            poly1305_valid=True,
            ciphertext_len=len(ocr_data["ciphertext"]),
            encrypt_time_ms=encrypt_img_ms,
            decrypt_time_ms=decrypt_img_ms,
            total_process_ms=total_ms,
            gambar_valid=True,
            delivery_status="MQTT Received"
        )
        db.session.add(keamanan)

        # === Simpan Gambar ===
        gambar = Gambar(
            nama_file=gambar_data["nama_file"],
            tipe="crop",
            resolusi="400x130",
            ukuran_byte=gambar_data["ukuran_byte"],
            ukuran_terenkripsi=gambar_data["ukuran_terenkripsi"],
            pelanggaran_id=pelanggaran.id
        )
        db.session.add(gambar)

        db.session.commit()
        print(f"✅ Data berhasil disimpan (plat: {payload['plat_nomor']}, decrypt: {decrypt_img_ms} ms)")

    except Exception as e:
        print(f"❌ Gagal menyimpan ke database: {e}")
