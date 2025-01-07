import os
import io
import base64
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber_extract
import pymupdf_extract
import pdfminer_extract
from profiler import profile_func
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route('/extract', methods=['POST'])
def extract_pdf():
    """
    API endpoint for PDF text extraction.
    Supports file upload and base64 encoded PDF.
    """
    try:
        extractor = 'pdfplumber'  # Default extractor
        # Check if file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if 'extractor' in request.form:
                extractor = request.form['extractor']
            if not file:
                return jsonify({'error': 'No file uploaded'}), 400

            # Read file bytes
            pdf_bytes = file.read()

        # Check for base64 content in JSON body
        elif request.is_json:
            pdf_base64 = request.json.get('pdf_base64')
            if 'extractor' in request.json:
                extractor = request.json['extractor']
            if not pdf_base64:
                return jsonify({'error': 'No PDF content provided'}), 400

            # Decode base64
            pdf_bytes = base64.b64decode(pdf_base64)

        else:
            return jsonify({'error': 'Unsupported request format'}), 400

        if extractor == 'pdfplumber':
            results = pdfplumber_extract.PDFTextExtractor().extract_blocks(io.BytesIO(pdf_bytes))
            # pdfplumber_extractor = profile_func(
            #     pdfplumber_extract.extract_pdf_blocks, 'pdfplumber')
            # results = pdfplumber_extractor(io.BytesIO(pdf_bytes))
        elif extractor == 'pymupdf':
            results = pymupdf_extract.convert_to_custom_format(
                pymupdf_extract.extract_text_blocks(pdf_bytes))
            # pymupdf_extractor = profile_func(
            #     pymupdf_extract.extract_text_blocks, 'pymupdf')
            # results = pymupdf_extract.convert_to_custom_format(
            #     pymupdf_extractor(pdf_bytes))

        elif extractor == 'pdfminer':
            results = pdfminer_extract.PDFTextExtractor().extract_blocks(
                io.BytesIO(pdf_bytes))
            # pdfminer_extractor = profile_func(
            #     pdfminer_extract.extract_pdf_blocks_pdfminer, 'pdfminer')
            # results = pdfminer_extractor(io.BytesIO(pdf_bytes))

        # Return results
        return json.dumps(results)

    except Exception as e:
        print(f'Error: {e}')
        print(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/', methods=['GET'])
def index():
    """
    Simple index page with usage instructions.
    """
    return """
    <h1>PDF Text Extractor API</h1>
    <p>Use POST /extract endpoint with:</p>
    <ul>
        <li>Multipart form-data file upload</li>
        <li>JSON with base64 encoded PDF content</li>
    </ul>
    <h2>Example Curl Commands:</h2>
    <pre>
    # File Upload
    curl -F "file=@document.pdf" http://localhost:5000/extract

    # Base64 JSON
    curl -X POST -H "Content-Type: application/json" \
         -d '{"pdf_base64":"base64_encoded_pdf_content"}' \
         http://localhost:5000/extract
    </pre>
    """


def create_app():
    """
    Create and configure the Flask application.
    """
    # Set max file size to 50MB
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
    return app


if __name__ == '__main__':
    # Configurable port and host
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')

    # Run the Flask app
    create_app().run(host=host, port=port, debug=True)
