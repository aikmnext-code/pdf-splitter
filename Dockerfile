# Python 3.11の軽量イメージを使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY main.py .

# Cloud Runで実行するためのコマンド (gunicornを使用)
# タイムアウトを0に設定してCloud Run側の制御に任せる
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app

# PDFページを画像変換するための poppler（pdf2image が内部で使用）
# OCRによる自動回転判定のための Tesseract
RUN apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-jpn poppler-utils