from flask import Blueprint, render_template, redirect, url_for, request
from datetime import datetime
from collections import Counter
from app.models import Pelanggaran   # ✅ BENAR, karena 'models.py
from .. import db
from sqlalchemy.orm import joinedload


main = Blueprint('main', __name__)

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
    return f"{h}, {dt.day} {b} {dt.year} - {dt.strftime('%H:%M')}"


@main.route('/')
def index():
    return redirect(url_for('main.dashboard'))


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



@main.route('/data')
def data():
    page = request.args.get('page', 1, type=int)
    per_page = 5

    pagination = Pelanggaran.query.options(joinedload(Pelanggaran.gambars))\
        .order_by(Pelanggaran.waktu.desc())\
        .paginate(page=page, per_page=per_page)

    return render_template('data.html', data=pagination.items, pagination=pagination)



@main.route('/detail/<int:id>')
def detail(id):
    record = Pelanggaran.query.get_or_404(id)
    return render_template('detail.html', record=record)


@main.route('/keamanan')
def keamanan():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    pagination = Pelanggaran.query.order_by(Pelanggaran.waktu.desc()).paginate(page=page, per_page=per_page)
    return render_template('keamanan.html', data=pagination.items, pagination=pagination)


@main.route('/keamanan/detail/<int:id>')
def keamanan_detail(id):
    record = Pelanggaran.query.get_or_404(id)
    return render_template('keamanan_detail.html', record=record)
