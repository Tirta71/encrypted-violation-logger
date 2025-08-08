import glob
import json
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, Response
from datetime import datetime
from collections import Counter
from app.models import Pelanggaran   # ✅ BENAR, karena 'models.py
from .. import db
from sqlalchemy.orm import joinedload
import os
from flask import current_app
from deteksi_server import gen_frames  # import fungsi streaming
from flask import send_file

main = Blueprint('main', __name__)

# di atas semua route
latest_ocr_result = {"plat": "-", "waktu": None}

# Filter waktu lokal
@main.app_template_filter('datetimeformat')
def datetimeformat(value):
    hari = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }
    bulan = {
        'January': 'Januari', 'February': 'Februari', 'March': 'Maret',
        'April': 'April', 'May': 'Mei', 'June': 'Juni', 'July': 'Juli',
        'August': 'Agustus', 'September': 'September', 'October': 'Oktober',
        'November': 'November', 'December': 'Desember'
    }
    dt = value
    h = hari[dt.strftime('%A')]
    b = bulan[dt.strftime('%B')]
    return f"{h}, {dt.day} {b} {dt.year} - {dt.strftime('%H:%M:%S')}"



@main.route('/')
def index():
    return redirect(url_for('main.dashboard'))

#Route Dashboard
@main.route('/dashboard')
def dashboard():
    data = Pelanggaran.query.options(joinedload(Pelanggaran.keamanan)).all()
    total = len(data)
    valid = sum(1 for p in data if p.keamanan and p.keamanan.poly1305_valid)
    invalid = total - valid

    tanggal_list = [p.waktu.strftime("%d-%m") for p in data]
    counter = Counter(tanggal_list)
    sorted_items = sorted(counter.items(), key=lambda x: datetime.strptime(x[0], "%d-%m"))

    chart_labels = [item[0] for item in sorted_items]
    chart_data = [item[1] for item in sorted_items]

    return render_template('dashboard.html', total=total, valid=valid, invalid=invalid,
                           chart_labels=chart_labels, chart_data=chart_data)


# Route Riwayat Pelanggaran
@main.route('/data')
def data():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    pagination = Pelanggaran.query.options(joinedload(Pelanggaran.gambars))\
        .order_by(Pelanggaran.waktu.desc())\
        .paginate(page=page, per_page=per_page)

    return render_template('data.html', data=pagination.items, pagination=pagination)


# Route Detail Riwayat Pelanggaran
@main.route('/detail/<int:id>')
def detail(id):
    record = Pelanggaran.query.get_or_404(id)
    return render_template('detail.html', record=record)



# Routes Halaman Live Stream
@main.route('/stream')
def stream():
    records = Pelanggaran.query.order_by(Pelanggaran.waktu.desc()).limit(3).all()
    return render_template('stream.html', records=records)



# Routes Pengecekan Data Masuk
@main.route('/api/latest-time')
def latest_time():
    latest = Pelanggaran.query.order_by(Pelanggaran.waktu.desc()).first()
    if latest and latest.waktu:
        return jsonify({"last_time": latest.waktu.isoformat()})
    return jsonify({"last_time": None})

# Routes Untuk Menampilkan Capture Image
@main.route('/stream/latest-image')
def latest_image():
    folder_path = os.path.join(current_app.root_path, '..', 'logs', 'pelanggaran')
    folder_path = os.path.abspath(folder_path)

    if not os.path.exists(folder_path):
        return "Folder logs/pelanggaran tidak ditemukan", 404

    folders = sorted(os.listdir(folder_path), reverse=True)
    for folder in folders:
        image_path = os.path.join(folder_path, folder, 'gambar.jpg')
        if os.path.exists(image_path):
            print("Serving:", image_path)
            return send_file(image_path, mimetype='image/jpeg')

    return "Gambar tidak ditemukan", 404

@main.route('/api/latest-records')
def latest_records():
    records = Pelanggaran.query.order_by(Pelanggaran.waktu.desc()).limit(3).all()
    result = []

    for r in records:
        result.append({
            "waktu": r.waktu.strftime("%d-%m-%Y %H:%M:%S"),
            "plat_nomor": r.plat_nomor or "Belum tersedia",
            "confidence": r.confidence or 0,
            "poly1305_valid": r.keamanan.poly1305_valid if r.keamanan else None,
            "gambar": url_for('static', filename='gambar_plat/' + r.gambars[0].nama_file) if r.gambars else None
        })

    return jsonify(result)


# Video Frame Deteksi Objek
@main.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
    


# Routes Page Keamanan

# Main Route Keamanan
@main.route('/keamanan')
def keamanan():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    pagination = Pelanggaran.query.order_by(Pelanggaran.waktu.desc()).paginate(page=page, per_page=per_page)
    data = pagination.items

    # --- baca log VALID ---
    log_valid_map = {}
    for filepath in glob.glob("logs/valid/*.json"):
        try:
            with open(filepath, "r") as f:
                log_data = json.load(f)
                log_id = log_data.get("id_pelanggaran")
                if log_id is not None:
                    log_valid_map[int(log_id)] = log_data
        except Exception as e:
            print(f"Gagal baca log valid: {filepath} - {e}")

    # --- baca log INVALID ---
    log_invalid_map = {}
    for filepath in glob.glob("logs/invalid/*.json"):
        try:
            with open(filepath, "r") as f:
                log_data = json.load(f)
                log_id = log_data.get("id_pelanggaran")
                if log_id is not None:
                    log_invalid_map[int(log_id)] = log_data
        except Exception as e:
            print(f"Gagal baca log invalid: {filepath} - {e}")

    # tempelkan ringkasan ke item
    for item in data:
        # valid
        if item.id in log_valid_map:
            item.valid_logged = True
            payload = log_valid_map[item.id].get("payload", {})
            item.valid_log_summary = f"Plat: {payload.get('plat_nomor', 'N/A')} | Confidence: {payload.get('confidence', 'N/A')}"
        else:
            item.valid_logged = False
            item.valid_log_summary = ""

        # invalid
        if item.id in log_invalid_map:
            item.invalid_logged = True
            payload = log_invalid_map[item.id].get("payload", {})
            ket = log_invalid_map[item.id].get("keterangan", "")
            item.invalid_log_summary = f"Plat: {payload.get('plat_nomor', 'N/A')} | Alasan: {ket or 'INVALID'}"
        else:
            item.invalid_logged = False
            item.invalid_log_summary = ""

    return render_template('keamanan.html', data=data, pagination=pagination)



# Routes Download Log Keamanan Data
@main.route('/keamanan/download_txt/<int:id>')
def download_log_as_txt(id):
    log_path = os.path.abspath(os.path.join(current_app.root_path, "..", "logs", "valid", f"{id}.json"))

    if not os.path.exists(log_path):
        return f"❌ Log valid untuk ID {id} tidak ditemukan.", 404

    with open(log_path, "r") as file:
        data = json.load(file)

    payload = data.get("payload", {})
    ocr = payload.get("ocr", {})
    gambar = payload.get("gambar", {})

    def row(label, value, width=27):
        value_str = str(value)
        if len(value_str) > 80:
            value_str = value_str[:77] + "..."
        return f"| {label:<{width}} | {value_str:<80} |\n"

    line = "=" * 114 + "\n"
    sep = "-" * 114 + "\n"

    content = ""
    content += line
    content += f"|{'LOG PELANGGARAN ID':^112}|\n"
    content += f"|{'ID ' + str(data.get('id_pelanggaran', '-')):^112}|\n"
    content += line

    content += row("Waktu Log", data.get("waktu_log", "-"))
    content += row("Plat Nomor", data.get("plat_nomor", "-"))
    content += row("Status", data.get("status", "-"))
    content += row("Keterangan", data.get("keterangan", "-"))

    content += sep
    content += f"|{'DETAIL PAYLOAD':^112}|\n"
    content += sep

    content += row("Timestamp", payload.get("timestamp", "-"))
    content += row("Device ID", payload.get("device_id", "-"))
    content += row("Confidence", f"{payload.get('confidence', '-')}%")
    content += row("Plat Nomor (OCR)", payload.get("plat_nomor", "-"))

    content += sep
    content += f"|{'ENKRIPSI OCR':^112}|\n"
    content += sep

    content += row("Nonce", ocr.get("nonce", "-"))
    content += row("Ciphertext", ocr.get("ciphertext", "-"))
    content += row("Poly1305 Tag", ocr.get("poly1305_tag", "-"))

    content += sep
    content += f"|{'ENKRIPSI GAMBAR':^112}|\n"
    content += sep

    content += row("Nama File", gambar.get("nama_file", "-"))
    content += row("Ukuran (Byte)", gambar.get("ukuran_byte", "-"))
    content += row("Ukuran Terenkripsi", gambar.get("ukuran_terenkripsi", "-"))
    content += row("Nonce", gambar.get("nonce", "-"))

    ciphertext = gambar.get("ciphertext", "")
    preview = ciphertext[:80] + ("..." if len(ciphertext) > 80 else "")
    content += row("Ciphertext", preview)
    content += row("Total Panjang Cipher", len(ciphertext))

    content += line

    return Response(
        content,
        mimetype='text/plain',
        headers={
            "Content-Disposition": f"attachment; filename=log_valid_{id}.txt"
        }
    )

@main.route('/keamanan/download_txt_invalid/<int:id>')
def download_log_invalid_as_txt(id):
    log_path = os.path.abspath(os.path.join(current_app.root_path, "..", "logs", "invalid", f"{id}.json"))

    if not os.path.exists(log_path):
        return f"❌ Log invalid untuk ID {id} tidak ditemukan.", 404

    with open(log_path, "r") as file:
        data = json.load(file)

    payload = data.get("payload", {})
    ocr = payload.get("ocr", {})
    gambar = payload.get("gambar", {})

    def row(label, value, width=27):
        value_str = str(value)
        if len(value_str) > 80:
            value_str = value_str[:77] + "..."
        return f"| {label:<{width}} | {value_str:<80} |\n"

    line = "=" * 114 + "\n"
    sep = "-" * 114 + "\n"

    content = ""
    content += line
    content += f"|{'LOG PELANGGARAN (INVALID) ID':^112}|\n"
    content += f"|{'ID ' + str(data.get('id_pelanggaran', '-')):^112}|\n"
    content += line

    content += row("Waktu Log", data.get("waktu_log", "-"))
    content += row("Plat Nomor", data.get("plat_nomor", "-"))
    content += row("Status", data.get("status", "-"))
    content += row("Keterangan", data.get("keterangan", "-"))

    content += sep
    content += f"|{'DETAIL PAYLOAD':^112}|\n"
    content += sep

    content += row("Timestamp", payload.get("timestamp", "-"))
    content += row("Device ID", payload.get("device_id", "-"))
    content += row("Confidence", f"{payload.get('confidence', '-')}%")
    content += row("Plat Nomor (OCR)", payload.get("plat_nomor", "-"))

    content += sep
    content += f"|{'ENKRIPSI OCR':^112}|\n"
    content += sep

    content += row("Nonce", ocr.get("nonce", "-"))
    content += row("Ciphertext", ocr.get("ciphertext", "-"))
    content += row("Poly1305 Tag", ocr.get("poly1305_tag", "-"))

    content += sep
    content += f"|{'ENKRIPSI GAMBAR':^112}|\n"
    content += sep

    content += row("Nama File", gambar.get("nama_file", "-"))
    content += row("Ukuran (Byte)", gambar.get("ukuran_byte", "-"))
    content += row("Ukuran Terenkripsi", gambar.get("ukuran_terenkripsi", "-"))
    content += row("Nonce", gambar.get("nonce", "-"))

    ciphertext = gambar.get("ciphertext", "")
    preview = ciphertext[:80] + ("..." if len(ciphertext) > 80 else "")
    content += row("Ciphertext", preview)
    content += row("Total Panjang Cipher", len(ciphertext))

    content += line

    return Response(
        content,
        mimetype='text/plain',
        headers={
            "Content-Disposition": f"attachment; filename=log_invalid_{id}.txt"
        }
    )








# Routes Detail Keamanan
@main.route('/keamanan/detail/<int:id>')
def keamanan_detail(id):
    record = Pelanggaran.query.get_or_404(id)
    return render_template('keamanan_detail.html', record=record)


# @main.route('/upload_stream', methods=['POST'])
# def upload_stream():
#     image = request.files['image']
#     # Simpan ke static/stream.jpg (folder static sejajar dengan run.py)
#     save_path = os.path.join(current_app.root_path, '..', 'static', 'stream.jpg')
#     image.save(os.path.abspath(save_path))
#     return 'OK'

