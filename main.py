import os
import base64
import io
from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

app = Flask(__name__)

# -------------------------------
# OCRで回転角度を検出
# -------------------------------
def detect_rotation(image):
    try:
        osd = pytesseract.image_to_osd(
            image,
            config="--psm 0"
        )
        print("OSD RESULT:", osd)

        for line in osd.split("\n"):
            if "Rotate" in line:
                return int(line.split(":")[1].strip())

    except Exception as e:
        print("OCR ERROR:", e)

    return 0


# -------------------------------
# PDFを1ページずつ回転補正
# -------------------------------
def auto_rotate_pdf(pdf_bytes: bytes) -> bytes:
    print("AUTO ROTATE STARTED")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    corrected_images = []

    for page_number in range(total_pages):
        print(f"Processing page {page_number+1}/{total_pages}")

        # 1ページのみ画像化（省メモリ）
        images = convert_from_bytes(
            pdf_bytes,
            dpi=100,
            first_page=page_number + 1,
            last_page=page_number + 1
        )

        if not images:
            continue

        img = images[0]

        rotation = detect_rotation(img)

        if rotation != 0:
            img = img.rotate(-rotation, expand=True)

        corrected_images.append(img)

    # 再PDF化
    output_buffer = io.BytesIO()
    corrected_images[0].save(
        output_buffer,
        format="PDF",
        save_all=True,
        append_images=corrected_images[1:]
    )

    print("AUTO ROTATE FINISHED")

    return output_buffer.getvalue()

    
# -------------------------------
# メインAPI
# -------------------------------
@app.route('/', methods=['POST'])
def split_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400

        pdf_base64 = data.get('pdf_base64')
        ranges = data.get('ranges')

        if not pdf_base64 or not ranges:
            return jsonify({'error': 'Missing pdf_base64 or ranges'}), 400

        # Base64 → bytes
        original_pdf_bytes = base64.b64decode(pdf_base64)

        # 🔥 ① 先に全ページ回転補正
        rotated_pdf_bytes = auto_rotate_pdf(original_pdf_bytes)

        # 🔥 ② 補正済PDFを読み込む
        reader = PdfReader(io.BytesIO(rotated_pdf_bytes))
        total_pages = len(reader.pages)

        split_files = []

        # 🔥 ③ 分割処理
        for r in ranges:
            start_page = r.get('start')
            end_page = r.get('end')

            if start_page is None or end_page is None:
                continue

            start_idx = int(start_page) - 1
            end_idx = int(end_page)

            if start_idx < 0:
                start_idx = 0
            if end_idx > total_pages:
                end_idx = total_pages
            if start_idx >= end_idx:
                continue

            writer = PdfWriter()

            for i in range(start_idx, end_idx):
                writer.add_page(reader.pages[i])

            output_buffer = io.BytesIO()
            writer.write(output_buffer)

            split_files.append({
                'base64': base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            })

        return jsonify(split_files)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
