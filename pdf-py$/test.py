
import fitz
import json
import os

results = {
    'pages': [],
    'dimensions': [],
    'total_pages': 0,
    'error': None
}

pdf_bytes = open(
    '/home/sudil/projects/pdf-text-color/public/mytables.pdf', 'rb').read()
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

        # Write blocks to file
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'page_{page_num + 1}.json')

        with open(output_file, 'w') as f:
            json.dump(blocks, f, indent=4)

    document.close()

except Exception as e:
    print(f'Error: {e}')
