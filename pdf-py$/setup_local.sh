# setup_local.sh
#!/bin/bash
set -e

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run the application
python pdf_text_extractor.py