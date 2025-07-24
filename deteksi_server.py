import cv2
from ultralytics import YOLO

model = YOLO("model/best.pt")

def gen_frames():
    cap = cv2.VideoCapture("http://172.20.10.11:8080/video")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        results = model(frame)
        boxes = results[0].boxes

        for i, box in enumerate(boxes.xyxy):
            x1, y1, x2, y2 = [int(v) for v in box]
            conf = boxes.conf[i].item()
            class_id = int(boxes.cls[i].item())

            # Ambil nama kelas dari model
            label_name = model.names[class_id] if model.names else "plat_nomor"
            label_text = f"{label_name.upper()} {conf*100:.1f}%"  # Misal: PLAT_NOMOR 87.3%

            # Warna dan font
            color = (0, 200, 0)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2

            # Ukuran teks dan posisi label
            text_size, _ = cv2.getTextSize(label_text, font, font_scale, font_thickness)
            text_width, text_height = text_size

            label_rect_x1 = x1
            label_rect_y1 = y1 - text_height - 10 if y1 - text_height - 10 > 0 else y1 + 5
            label_rect_x2 = x1 + text_width + 10
            label_rect_y2 = label_rect_y1 + text_height + 6

            # Gambar kotak deteksi
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Gambar background label
            cv2.rectangle(frame, (label_rect_x1, label_rect_y1),
                          (label_rect_x2, label_rect_y2), color, -1)

            # Gambar teks
            cv2.putText(frame, label_text, (label_rect_x1 + 5, label_rect_y2 - 5),
                        font, font_scale, (255, 255, 255), font_thickness)

        # Encode frame ke JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
