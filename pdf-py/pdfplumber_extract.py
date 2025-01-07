from typing import List, Dict, Any
from pdfplumber import open as pdf_open
from pdfplumber.page import Page
from pdfminer.layout import LTTextContainer, LTChar, LTTextLineHorizontal
from geometry import Block, BoundingPoly

def detect_blocked_or_camouflaged_text(pdf_bytes):
    invisible_chars = {}
    with pdf_open(pdf_bytes) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            print(f"Analyzing page {page_number}...")
            invisible_chars[page_number] = []

            # Extract text with bounding boxes
            text_instances = page.extract_words()

            # Extract graphical elements (shapes and images)
            images = page.images
            shapes = page.rects + page.lines

            for text in text_instances:
                text_bbox = (text["x0"], text["top"], text["x1"], text["bottom"])
                text_str = text["text"]

                # Check for overlap with images
                for img in images:
                    image_bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                    if bbox_overlap(text_bbox, image_bbox):
                        print(f"Blocked text detected on page {page_number}: {text_str}")
                        invisible_chars[page_number].append(text)

                # Check for overlap with shapes
                for shape in shapes:
                    shape_bbox = (shape["x0"], shape["top"], shape["x1"], shape["bottom"])
                    if bbox_overlap(text_bbox, shape_bbox):
                        print(f"Blocked text detected (shape) on page {page_number}: {text_str}")
                        invisible_chars[page_number].append(text)

                # Check for camouflaged text (simplified example: same fill color)
                if "non_stroking_color" in text and text["non_stroking_color"] == (1, 1, 1):
                    print(f"Camouflaged text detected on page {page_number}: {text_str}")
                    invisible_chars[page_number].append(text)

def bbox_overlap(bbox1, bbox2):
    """Check if two bounding boxes overlap."""
    return not (bbox1[2] <= bbox2[0] or bbox1[0] >= bbox2[2] or
                bbox1[3] <= bbox2[1] or bbox1[1] >= bbox2[3])


class PDFTextExtractor:
    """Advanced PDF text extraction utility."""

    @staticmethod
    def _group_chars_to_words(page: Page, line_element: LTTextLineHorizontal) -> List[Dict[str, Any]]:
        """
        Group characters into words based on spacing.

        :param page: PDF page object
        :param line_element: Horizontal text line
        :return: List of word dictionaries
        """
        words = []
        current_word = []
        previous_char = None

        for char in filter(lambda c: isinstance(c, LTChar), line_element):
            if previous_char:
                # Determine word boundaries based on spacing
                if char.bbox[0] - previous_char.bbox[2] > 2 or previous_char.get_text().strip() == '':
                    if current_word:
                        words.append(PDFTextExtractor._create_word_block(
                            current_word, page.height))
                        current_word = []

            if char.get_text().strip():  # Ignore space characters
                current_word.append(char)
            previous_char = char

        # Add last word if exists
        if current_word:
            words.append(PDFTextExtractor._create_word_block(
                current_word, page.height))

        return words

    @staticmethod
    def _create_word_block(word_chars: List[LTChar], page_height: float) -> Dict[str, Any]:
        """
        Create a word block from character list.

        :param word_chars: List of characters in the word
        :param page_height: Height of the page for coordinate transformation
        :return: Word block dictionary
        """
        word_text = "".join(c.get_text().strip()
                            for c in word_chars)  # Strip whitespace
        x0 = min(c.bbox[0] for c in word_chars)
        x1 = max(c.bbox[2] for c in word_chars)
        top = page_height - min(c.bbox[1] for c in word_chars)
        bottom = page_height - max(c.bbox[3] for c in word_chars)
        return {
            "text": word_text,
            "x0": x0,
            "x1": x1,
            "top": top,
            "bottom": bottom
        }

    @staticmethod
    def extract_text_lines(page: Page) -> List[Dict[str, Any]]:
        """
        Extract text lines from a PDF page.

        :param page: PDF page object
        :return: List of line dictionaries
        """
        lines = []
        for element in page.layout:
            if isinstance(element, LTTextContainer):
                for line_element in element:
                    if isinstance(line_element, LTTextLineHorizontal):
                        text = line_element.get_text().replace("\n", "").strip()
                        words = PDFTextExtractor._group_chars_to_words(
                            page, line_element)

                        x0 = min(
                            word["x0"] for word in words) if words else line_element.bbox[0]
                        x1 = max(
                            word["x1"] for word in words) if words else line_element.bbox[2]
                        top = page.height - line_element.y0
                        bottom = page.height - line_element.y1

                        lines.append({
                            "x0": x0,
                            "x1": x1,
                            "top": top,
                            "bottom": bottom,
                            "text": text,
                            "words": words
                        })

        return lines

    def extract_blocks(self, pdf_bytes) -> List[Dict[str, Any]]:
        """
        Extract text blocks from PDF bytes.

        :param pdf_bytes: PDF file as bytes
        :return: List of page dictionaries with text annotations
        """
        document = []

        detect_blocked_or_camouflaged_text(pdf_bytes)

        with pdf_open(pdf_bytes, laparams={}) as pdf:
            for page_number, page in enumerate(pdf.pages):
                blocks = self._process_page(page, page_number)
                document.append({
                    "page": page_number + 1,
                    "textAnnotations": blocks,
                    "textPreview": " ".join(
                        word["text"]
                        for line in self.extract_text_lines(page)
                        for word in line["words"]
                    )
                })

        return document

    def _process_page(self, page: Page, page_number: int) -> List[Dict[str, Any]]:
        """
        Process a single PDF page.

        :param page: PDF page object
        :param page_number: Current page number
        :return: List of text block dictionaries
        """
        blocks = []

        # Create page block
        page_block = Block(
            block_type="PAGE",
            bounding_poly=BoundingPoly.from_bbox(
                (0, 0, page.width, page.height)),
            relationships=[{"type": "CHILD", "ids": []}]
        )
        blocks.append(page_block)

        # Process lines
        lines = self.extract_text_lines(page)
        for line_data in lines:
            # Create line block
            x0 = line_data["x0"]
            x1 = line_data["x1"]
            y0 = line_data["bottom"]
            y1 = line_data["top"]
            line_block = Block(
                block_type="LINE",
                description=line_data["text"],
                bounding_poly=BoundingPoly.from_bbox((x0, y0, x1, y1)),
                relationships=[{"type": "CHILD", "ids": []}]
            )
            page_block.relationships[0]["ids"].append(line_block.id)
            blocks.append(line_block)

            # Process words
            for word in line_data["words"]:
                x0 = word["x0"]
                x1 = word["x1"]
                y0 = word["bottom"]
                y1 = word["top"]
                word_block = Block(
                    block_type="WORD",
                    description=word["text"],
                    bounding_poly=BoundingPoly.from_bbox((x0, y0, x1, y1))
                )
                line_block.relationships[0]["ids"].append(word_block.id)
                blocks.append(word_block)

        # Sort blocks
        block_order = {"PAGE": 0, "LINE": 1, "WORD": 2}
        sorted_blocks = sorted(blocks, key=lambda block: (
            block_order[block.block_type], block.id))

        # Serialize blocks
        output_blocks = [block.to_dict() for block in sorted_blocks]

        return output_blocks
