# app/services/deteksi_pelanggaran.py

import os
import json
import base64
from datetime import datetime


def simpan_pelanggaran(payload):
    waktu = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join("logs", "pelanggaran", waktu)
    os.makedirs(folder, exist_ok=True)

    # Simpan payload
    with open(os.path.join(folder, "payload.json"), "w") as f:
        json.dump(payload, f, indent=2)

    # Simpan gambar jika ada
    if "gambar" in payload:
        try:
            img_data = base64.b64decode(payload["gambar"])
            with open(os.path.join(folder, "gambar.jpg"), "wb") as f:
                f.write(img_data)
            print("✅ Gambar pelanggaran disimpan.")
        except Exception as e:
            print(f"❌ Gagal menyimpan gambar: {e}")
