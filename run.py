from app import create_app
from app.mqtt.listener import mulai_listener
import threading
import os

app = create_app()

def start():
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("🚀 Menjalankan MQTT listener...")
        threading.Thread(target=mulai_listener, daemon=True).start()

if __name__ == '__main__':
    start()
    app.run(debug=True, host='0.0.0.0', port=5000)  # ← tambahan host dan port

