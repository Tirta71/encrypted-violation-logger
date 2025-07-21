# app/mqtt/listener.py

import paho.mqtt.client as mqtt
import ssl
import json
import certifi
from app import create_app
from app.services.simpan_data import simpan_ke_database
from app.services.deteksi_pelanggaran import simpan_pelanggaran

# Buat app context global
app = create_app()

# Konfigurasi
BROKER = "0fc5ab61ae91429d80cc08fc224eb005.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "tirta71"
PASSWORD = "hero1234"
TOPICS = [("plat/ocr", 1), ("plat/pelanggaran", 1)]


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Terkoneksi ke broker.")
        client.subscribe(TOPICS)
    else:
        print(f"❌ Gagal koneksi: {rc}")


def on_message(client, userdata, msg):
    print(f"📥 Topik: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        with app.app_context():
            if msg.topic == "plat/ocr":
                simpan_ke_database(payload)
            elif msg.topic == "plat/pelanggaran":
                simpan_pelanggaran(payload)
    except Exception as e:
        print(f"❌ Error: {e}")


def mulai_listener():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set(ca_certs=certifi.where(), tls_version=ssl.PROTOCOL_TLS)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)
    client.loop_forever()
