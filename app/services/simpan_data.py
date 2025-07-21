import base64
import os
import time
import json
from datetime import datetime
import paho.mqtt.client as mqtt
import certifi
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from app import db
from app.models import Pelanggaran, Keamanan, Gambar

# === MQTT Configuration ===
MQTT_BROKER = "0fc5ab61ae91429d80cc08fc224eb005.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "tirta71"
MQTT_PASSWORD = "hero1234"
MQTT_INVALID_TOPIC = "plat/ocr/invalid"

# === Static Key ===
KEY_B64 = "kKgTWK1FuLFlHrxRX8xlE7e9IYvqqMaI8CyZGhmmu6c="
KEY = base64.b64decode(KEY_B64)

# === Log File ===
LOG_DIR = "logs"
timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = os.path.join(LOG_DIR, f"log_{timestamp_str}.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)

# === Fungsi Dekripsi ===
def decrypt_chacha(nonce_b64, ciphertext_b64, tag_b64):
    try:
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        tag = base64.b64decode(tag_b64)

        chacha = ChaCha20Poly1305(KEY)
        start = time.perf_counter()
        plaintext = chacha.decrypt(nonce, ciphertext + tag, None)
        decrypt_time = round((time.perf_counter() - start) * 1000, 3)
        return plaintext, decrypt_time, True
    except Exception as e:
        return b"", 0, False

# === Fungsi Kirim Notifikasi MQTT ===
def kirim_mqtt_invalid(payload, alasan: str):
    try:
        client = mqtt.Client()
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.tls_set(ca_certs=certifi.where())
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        notif = {
            "status": "invalid",
            "plat_nomor": payload.get("plat_nomor", "UNKNOWN"),
            "timestamp": payload.get("timestamp"),
            "alasan": alasan
        }

        client.publish(MQTT_INVALID_TOPIC, json.dumps(notif), qos=1)
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        print("📡 Notifikasi INVALID dikirim ke MQTT.")
    except Exception as e:
        print(f"❌ Gagal kirim MQTT INVALID: {e}")

# === Fungsi Logging ke File ===

def simpan_log(payload: dict, status: str, keterangan: str, id_pelanggaran=None):
    print(f"[LOG] Menyimpan log status={status} untuk plat={payload.get('plat_nomor')} at {payload.get('timestamp')}")
    try:
        waktu_obj = datetime.fromisoformat(payload["timestamp"])
        waktu_str = waktu_obj.strftime('%Y-%m-%d %H:%M:%S')

        log_entry = {
            "id_pelanggaran": id_pelanggaran,
            "waktu_log": waktu_str,
            "plat_nomor": payload.get("plat_nomor", "UNKNOWN"),
            "status": status,
            "keterangan": keterangan,
            "payload": payload
        }

        # Buat folder berdasarkan status
        log_path = os.path.join(LOG_DIR, status)
        os.makedirs(log_path, exist_ok=True)

        # Nama file berdasarkan ID pelanggaran jika tersedia
        if id_pelanggaran is not None:
            log_filename = f"{id_pelanggaran}.json"
        else:
            log_filename = waktu_obj.strftime('%Y-%m-%d_%H-%M-%S') + ".json"

        log_file = os.path.join(log_path, log_filename)

        # Hindari log ganda untuk invalid/duplikat
        nama_file = payload.get("gambar", {}).get("nama_file", "UNKNOWN")
        if status in ["invalid", "duplikat"]:
            cache_file = os.path.join(log_path, ".invalid_logged.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    logged_files = json.load(f)
            else:
                logged_files = []

            if nama_file in logged_files:
                print(f"⚠️ Log {status.upper()} untuk '{nama_file}' sudah dicatat sebelumnya, dilewati.")
                return

            logged_files.append(nama_file)
            with open(cache_file, "w") as f:
                json.dump(logged_files, f, indent=2)

        # Tulis file log
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)

        print(f"📝 Log {status.upper()} ditulis:", log_file)

    except Exception as e:
        print(f"❌ Gagal menyimpan log {status}: {e}")




# === Fungsi Simpan ke Database ===
def simpan_ke_database(payload):
    try:
        waktu_obj = datetime.fromisoformat(payload["timestamp"])
        gambar_data = payload["gambar"]
        ocr_data = payload["ocr"]
        nama_file = gambar_data["nama_file"]

        if Gambar.query.filter_by(nama_file=nama_file).first():
            info = f"⚠️ Duplikat file: {nama_file} sudah ada di database."
            print(info)
            simpan_log(payload, "duplikat", info)
            return

        ocr_plain, decrypt_ocr_ms, ocr_valid = decrypt_chacha(
            ocr_data["nonce"], ocr_data["ciphertext"], ocr_data["poly1305_tag"]
        )
        gambar_bytes, decrypt_img_ms, gambar_valid = decrypt_chacha(
            gambar_data["nonce"], gambar_data["ciphertext"], gambar_data["poly1305_tag"]
        )

        alasan_ocr = ""
        alasan_gambar = ""

        if not ocr_valid:
            alasan_ocr = "Tag Poly1305 OCR tidak valid"
            print("❌", alasan_ocr)
            kirim_mqtt_invalid(payload, alasan_ocr)
            simpan_log(payload, "invalid", alasan_ocr)

        if not gambar_valid:
            alasan_gambar = "Tag Poly1305 Gambar tidak valid"
            print("❌", alasan_gambar)
            kirim_mqtt_invalid(payload, alasan_gambar)
            simpan_log(payload, "invalid", alasan_gambar)

        ocr_text = ocr_plain.decode("utf-8") if ocr_valid else ""
        encrypt_ocr_ms = round(ocr_data.get("encrypt_time_ms", 0), 3)
        encrypt_img_ms = round(gambar_data.get("encrypt_time_ms", 0), 3)
        total_ms = round(encrypt_img_ms + decrypt_img_ms, 3)

        save_dir = os.path.join("static", "gambar_plat")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, nama_file)
        if gambar_valid:
            with open(save_path, "wb") as f:
                f.write(gambar_bytes)

        pelanggaran = Pelanggaran(
            waktu=waktu_obj,
            plat_nomor=payload["plat_nomor"],
            confidence=payload["confidence"],
            device_id=payload["device_id"]
        )
        db.session.add(pelanggaran)
        db.session.commit()

        keamanan = Keamanan(
            pelanggaran_id=pelanggaran.id,
            nonce=gambar_data["nonce"],
            poly1305_tag=gambar_data["poly1305_tag"],
            poly1305_valid=gambar_valid,
            ciphertext_len=len(gambar_data["ciphertext"]),
            encrypt_time_ms=encrypt_img_ms,
            decrypt_time_ms=decrypt_img_ms,
            total_process_ms=total_ms,
            gambar_valid=gambar_valid,
            delivery_status="MQTT Received"
        )
        db.session.add(keamanan)

        gambar = Gambar(
            nama_file=nama_file,
            tipe="crop",
            resolusi="400x130",
            ukuran_byte=gambar_data["ukuran_byte"],
            ukuran_terenkripsi=gambar_data["ukuran_terenkripsi"],
            pelanggaran_id=pelanggaran.id
        )
        db.session.add(gambar)

        db.session.commit()
        status_final = "valid" if ocr_valid and gambar_valid else "invalid"
        info = f"✅ Data tersimpan dengan status {status_final.upper()}: {payload['plat_nomor']} | Waktu: {total_ms} ms"
        print(info)
        simpan_log(payload, status_final, info, id_pelanggaran=pelanggaran.id)



    except Exception as e:
        error_info = f"Gagal menyimpan ke database: {e}"
        print("❌", error_info)
        simpan_log(payload, "error", error_info)
