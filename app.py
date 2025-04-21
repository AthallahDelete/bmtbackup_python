from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import os
import uuid
import time

app = Flask(__name__)
CORS(app)


def get_laravel_endpoint(folder):
    base_url = os.getenv("LARAVEL_URL") or 'http://localhost:8000'
    if folder == 'file':
        return f'{base_url}/api/upload-image/ktp'
    elif folder == 'capJempol':
        return f'{base_url}/api/upload-image/fingerprint'
    return f'{base_url}/api/upload-image'


def ocr_ktp(image_data, api_key):
    url = 'https://api.ekycpro.com/v1/id_ocr/general'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-API-Key': api_key
    }
    data = {'img': image_data}

    try:
        response = requests.post(url, headers=headers, data=data)
        return response.json() if response.status_code == 200 else {
            "status": "INNER_ERROR",
            "message": "Service not available"
        }
    except Exception as e:
        return {"status": "ERROR", "message": f"Exception occurred: {str(e)}"}


@app.route('/process-ocr', methods=['POST'])
def process_ocr():
    try:
        data = request.json
        image_data = data.get('image', '').split(',')[1]
        api_key = os.getenv(
            'API_KEY'
        ) or 'XAenIDLIyaELTeasy001LLyoheIDueasyMwIkQAhFweNbLVBRjzwVbNqa001'

        unique_id = str(uuid.uuid4())
        filename = f"ktp_{unique_id}.jpg"

        upload_response = upload_to_laravel(filename,
                                            image_data,
                                            folder='file')

        if not upload_response.get("success"):
            print("Upload response gagal:", upload_response)
            return jsonify({
                "status": "ERROR",
                "message": "Gagal upload ke Laravel"
            }), 500

        result = ocr_ktp(image_data, api_key)
        print("OCR message content:", result.get('message'))
        if 'message' in result:
            ktp_data = result['message']
            ktp_data['pathfile'] = upload_response.get("url", "")
            return jsonify({"status": "success", "ktp_data": ktp_data})

        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route('/process-fingerprint', methods=['POST'])
def process_fingerprint():
    try:
        data = request.json
        fingerprint_data = data.get('fingerprint', '').split(',')[1]
        timestamp = int(time.time())
        filename = f"capJempol_{timestamp}.jpg"

        upload_response = upload_to_laravel(filename,
                                            fingerprint_data,
                                            folder='capJempol')
        if not upload_response.get("success"):
            print("Upload response gagal:", upload_response)
            return jsonify({
                "status": "ERROR",
                "message": "Gagal upload ke Laravel"
            }), 500

        return jsonify({
            "status": "success",
            "fingerprint_image_url": upload_response.get("url", "")
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "ERROR", "message": str(e)}), 500


def upload_to_laravel(filename, base64_data, folder=None, endpoint=None):
    try:
        if not endpoint:
            endpoint = get_laravel_endpoint(folder)

        files = {
            'image': (filename, base64.b64decode(base64_data), 'image/jpeg'),
        }

        response = requests.post(endpoint, files=files)
        print("Raw response Laravel:", response.text)
        return response.json()
    except Exception as e:
        print("Error saat upload:", str(e))
        return {"success": False, "error": str(e)}


@app.route('/')
def index():
    return 'Flask server is running!'


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, host='0.0.0.0', port=port)