import os
import io
import json
import uuid
import base64
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


def generate_unique_id():
    """
    Generate a unique identifier.
    """
    return str(uuid.uuid4()).replace('-', '')[:22]


def convert_to_custom_format(document):
    """
    Convert PyMuPDF extraction results to custom block format with bounding poly vertices as ratios.

    Args:
        document (dict): PyMuPDF extraction results

    Returns:
        list: Formatted document pages with text annotations and relationships
    """
    pages_output = []

    for page_num, page in enumerate(document['pages']):
        text_annotations = []
        page_id = generate_unique_id()
        page_text_preview = []

        # Get the page size
        page_width = document['dimensions'][page_num]['width']
        page_height = document['dimensions'][page_num]['height']

        # Collect LINE and WORD blocks
        line_ids = []
        for line in page:
            line_id = generate_unique_id()
            line_ids.append(line_id)

            # Normalize LINE bounding poly vertices
            line_block = {
                "blockType": "LINE",
                "description": line['line_text'],
                "boundingPoly": {
                    "vertices": [
                        {"x": line['bbox']['x1'], "y": line['bbox']['y1']},
                        {"x": line['bbox']['x2'], "y": line['bbox']['y1']},
                        {"x": line['bbox']['x2'], "y": line['bbox']['y2']},
                        {"x": line['bbox']['x1'], "y": line['bbox']['y2']}
                    ]
                },
                "id": line_id,
                "relationships": []
            }
            page_text_preview.append(line['line_text'])

            word_ids = []
            # Normalize WORD bounding poly vertices
            for word in line['words']:
                word_id = generate_unique_id()
                word_ids.append(word_id)

                word_block = {
                    "blockType": "WORD",
                    "description": word['text'],
                    "boundingPoly": {
                        "vertices": [
                            {"x": word['bbox']['x1'], "y": word['bbox']['y1']},
                            {"x": word['bbox']['x2'], "y": word['bbox']['y1']},
                            {"x": word['bbox']['x2'], "y": word['bbox']['y2']},
                            {"x": word['bbox']['x1'], "y": word['bbox']['y2']}
                        ]
                    },
                    "id": word_id
                }
                text_annotations.append(word_block)

            # Add WORD relationships to LINE block
            if word_ids:
                line_block["relationships"].append({
                    "type": "CHILD",
                    "ids": word_ids
                })

            text_annotations.append(line_block)

        # Create PAGE block
        page_block = {
            "blockType": "PAGE",
            "id": page_id,
            "boundingPoly": {
                "vertices": [
                    {"x": 0, "y": 0},
                    {"x": page_width, "y": 0},
                    {"x": page_width, "y": page_height},
                    {"x": 0, "y": page_height}
                ]
            },
            "relationships": []
        }

        # Add LINE relationships to PAGE block
        if line_ids:
            page_block["relationships"].append({
                "type": "CHILD",
                "ids": line_ids
            })

        # Add PAGE block as the first block
        text_annotations.insert(0, page_block)

        # Filter out LINE blocks with empty text and no relationships
        text_annotations = [block for block in text_annotations if (
            block['blockType'] != 'LINE' or block['description']) or block['relationships']]

        # Order text_annotations blocks in: PAGE -> LINE -> WORD
        text_annotations = sorted(text_annotations, key=lambda x: (
            x['blockType'] != 'PAGE', x['blockType'] != 'LINE'))

        pages_output.append({
            "page": page_num + 1,
            "textAnnotations": text_annotations,
            "textPreview": " ".join(page_text_preview)
        })

    return pages_output


def extract_text_blocks(pdf_bytes):
    """
    Extract text blocks with positioning from PDF bytes.

    Args:
        pdf_bytes (bytes): PDF file content as bytes

    Returns:
        dict: Extracted text block information
    """
    results = {
        'pages': [],
        'dimensions': [],
        'total_pages': 0,
        'error': None
    }

    try:
        # Open PDF from bytes
        document = fitz.open(stream=pdf_bytes, filetype='pdf')
        results['total_pages'] = len(document)

        for page_num, page in enumerate(document):
            page_blocks = []
            page_rect = page.rect  # Get page dimensions
            results['dimensions'].append(
                {'width': page_rect.width, 'height': page_rect.height})

            # Get text blocks
            blocks = page.get_text("dict")['blocks']
            words = page.get_text("words")

            for word in words:
                line_words = []
                x0, y0, x1, y1, text, block_no, line_no, word_no = word
                line_words.append({
                    'text': text,
                    'bbox': {
                        'x1': round(x0, 2),
                        'y1': round(y0, 2),
                        'x2': round(x1, 2),
                        'y2': round(y1, 2)
                    }
                })

                line_text = text
                if line_text.strip():
                    page_blocks.append({
                        'line_text': line_text.strip(),
                        'bbox': {
                            'x1': round(x0, 2),
                            'y1': round(y0, 2),
                            'x2': round(x1, 2),
                            'y2': round(y1, 2)
                        },
                        'words': line_words
                    })

            # for block in blocks:
            #     if block['type'] == 0:  # Text block
            #         block_number = block['number']
            #         for line_index, line in enumerate(block['lines']):
            #             # line_text = ''
            #             line_words = []

            #             # iterate through words
            #             for word in words:
            #                 x0, y0, x1, y1, text, block_no, line_no, word_no = word
            #                 if block_no == block_number and line_no == line_index and text.strip():
            #                     line_words.append({
            #                         'text': text,
            #                         'bbox': {
            #                             'x1': round(x0, 2),
            #                             'y1': round(y0, 2),
            #                             'x2': round(x1, 2),
            #                             'y2': round(y1, 2)
            #                         }
            #                     })
            #                     # line_text += text + ' '


            #             # for span in line['spans']:
            #             #     for word in span['text'].split():
            #             #         # Get individual word details
            #             #         word_rect = fitz.Rect(
            #             #             span['origin'][0],
            #             #             line['bbox'][1],
            #             #             span['origin'][0] + span['size'],
            #             #             line['bbox'][3]
            #             #         )

            #             #         line_words.append({
            #             #             'text': word,
            #             #             'bbox': {
            #             #                 'x1': round(word_rect.x0, 2),
            #             #                 'y1': round(word_rect.y0, 2),
            #             #                 'x2': round(word_rect.x1, 2),
            #             #                 'y2': round(word_rect.y1, 2)
            #             #             }
            #             #         })
            #             #         line_text += word + ' '
                        
            #             # get line_text from line['spans']
            #             line_text = ' '.join([span['text'] for span in line['spans']])

            #             if line_text.strip():
            #                 page_blocks.append({
            #                     'line_text': line_text.strip(),
            #                     'bbox': {
            #                         'x1': round(line['bbox'][0], 2),
            #                         'y1': round(line['bbox'][1], 2),
            #                         'x2': round(line['bbox'][2], 2),
            #                         'y2': round(line['bbox'][3], 2)
            #                     },
            #                     'words': line_words
            #                 })

            results['pages'].append(page_blocks)

        document.close()
        return results

    except Exception as e:
        print(f'Error: {e}')
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
        return results


@app.route('/extract', methods=['POST'])
def extract_pdf():
    """
    API endpoint for PDF text extraction.
    Supports file upload and base64 encoded PDF.
    """
    try:
        # Check if file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if not file:
                return jsonify({'error': 'No file uploaded'}), 400

            # Read file bytes
            pdf_bytes = file.read()

        # Check for base64 content in JSON body
        elif request.is_json:
            pdf_base64 = request.json.get('pdf_base64')
            if not pdf_base64:
                return jsonify({'error': 'No PDF content provided'}), 400

            # Decode base64
            pdf_bytes = base64.b64decode(pdf_base64)

        else:
            return jsonify({'error': 'Unsupported request format'}), 400

        # Extract text blocks
        results = extract_text_blocks(pdf_bytes)

        # Convert to custom format
        custom_format = convert_to_custom_format(results)

        # Return results
        return jsonify(custom_format)

    except Exception as e:
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
