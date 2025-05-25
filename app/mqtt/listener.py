import paho.mqtt.client as mqtt
import ssl
import json
from app.services.simpan_data import simpan_ke_database  # pastikan ini ada
import certifi
# === Callback ketika pesan diterima ===
from app import create_app  # tambahkan ini di atas
app = create_app()          # buat app 1x di global scope

# === MQTT Config ===
BROKER = "0fc5ab61ae91429d80cc08fc224eb005.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "plat/ocr"
USERNAME = "tirta71"
PASSWORD = "hero1234"




def on_message(client, userdata, msg):
    print(f"📥 Pesan diterima dari topik {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        print(json.dumps(payload, indent=2))

        # ⬇️ Bungkus dengan app context
        with app.app_context():
            simpan_ke_database(payload)

    except Exception as e:
        print(f"❌ Gagal memproses pesan: {e}")


# === Callback saat terkoneksi ===
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Terkoneksi ke HiveMQ.")
        client.subscribe(TOPIC)
    else:
        print(f"❌ Gagal koneksi. Kode: {rc}")

# === Setup MQTT Client ===
def mulai_listener():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set(ca_certs=certifi.where(), certfile=None, keyfile=None, tls_version=ssl.PROTOCOL_TLS)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)
    client.loop_forever()
