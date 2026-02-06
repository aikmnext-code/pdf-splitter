import os
import base64
import io
import json
from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)

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

        # Base64デコード
        pdf_bytes = base64.b64decode(pdf_base64)
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)

        split_files = []

        for r in ranges:
            # Geminiは1始まりのページ番号を返すと想定
            start_page = r.get('start')
            end_page = r.get('end')

            if start_page is None or end_page is None:
                continue

            # 1-based index を 0-based index に変換
            start_idx = int(start_page) - 1
            end_idx = int(end_page) # rangeの終了は排他なので、endそのままでOK (例: 1ページ目のみなら 0:1)

            # 範囲チェック
            if start_idx < 0: start_idx = 0
            if end_idx > total_pages: end_idx = total_pages
            if start_idx >= end_idx: continue

            writer = PdfWriter()
            # 指定範囲のページを追加
            for i in range(start_idx, end_idx):
                writer.add_page(reader.pages[i])

            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            split_pdf_bytes = output_buffer.getvalue()

            # Base64エンコードしてリストに追加
            split_files.append({
                'base64': base64.b64encode(split_pdf_bytes).decode('utf-8')
            })

        return jsonify(split_files)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Cloud Runは環境変数PORTで指定されたポートでリッスンする必要がある
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
