from . import db
from datetime import datetime

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), unique=True, nullable=False)

    pelanggarans = db.relationship('Pelanggaran', backref='device', lazy=True)


class Pelanggaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    waktu = db.Column(db.DateTime, default=datetime.utcnow)
    plat_nomor = db.Column(db.String(50))
    confidence = db.Column(db.Float)

    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)

    # 1:N relasi ke gambar
    gambars = db.relationship('Gambar', backref='pelanggaran', lazy=True)

    # 1:1 relasi ke keamanan
    keamanan = db.relationship('Keamanan', uselist=False, backref='pelanggaran')


class Gambar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_file = db.Column(db.String(100), nullable=False)
    tipe = db.Column(db.String(30))  
    resolusi = db.Column(db.String(20))  
    ukuran_byte = db.Column(db.Integer)  
    ukuran_terenkripsi = db.Column(db.Integer)  

    pelanggaran_id = db.Column(db.Integer, db.ForeignKey('pelanggaran.id'), nullable=False)



class Keamanan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    nonce = db.Column(db.String(100))
    poly1305_tag = db.Column(db.String(100))
    poly1305_valid = db.Column(db.Boolean)
    
    encrypt_time_ms = db.Column(db.Float)
    decrypt_time_ms = db.Column(db.Float)
    total_process_ms = db.Column(db.Float)
    ciphertext_len = db.Column(db.Integer)

    gambar_valid = db.Column(db.Boolean)  
    delivery_status = db.Column(db.String(50))

    pelanggaran_id = db.Column(db.Integer, db.ForeignKey('pelanggaran.id'), nullable=False)
