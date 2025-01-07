from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTTextLineHorizontal, LTPage
from geometry import Block, BoundingPoly
from typing import List, Dict, Any


class PDFTextExtractor:
    """Advanced PDF text extraction utility."""

    @staticmethod
    def _group_chars_to_words(line_element: LTTextLineHorizontal, page_height: float) -> List[Dict[str, Any]]:
        """
        Group characters into words based on spacing.

        :param page: PDF page object
        :param line_element: Horizontal text line
        :return: List of word dictionaries
        """
        words = []
        current_word = []
        previous_char = None

        # Split line into words based on space char
        for char in filter(lambda c: isinstance(c, LTChar), line_element):
            if previous_char:
                # Check if there is a space between characters
                if previous_char.get_text().strip() == '':
                    if current_word:
                        words.append(PDFTextExtractor._create_word_block(
                            current_word, page_height))
                        current_word = []

            if char.get_text().strip():  # Ignore space characters
                current_word.append(char)
            previous_char = char

        # Add last word if exists
        if current_word:
            words.append(PDFTextExtractor._create_word_block(
                current_word, page_height))

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
    def extract_text_lines(page_layout: LTPage) -> List[Dict[str, Any]]:
        """
        Extract text lines from a PDF page.

        :param page: PDF page object
        :return: List of line dictionaries
        """
        lines = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for line_element in element:
                    if isinstance(line_element, LTTextLineHorizontal):
                        text = line_element.get_text().replace("\n", "").strip()
                        words = PDFTextExtractor._group_chars_to_words(
                            line_element, page_layout.height)

                        x0 = min(
                            word["x0"] for word in words) if words else line_element.bbox[0]
                        x1 = max(
                            word["x1"] for word in words) if words else line_element.bbox[2]
                        top = page_layout.height - line_element.y0
                        bottom = page_layout.height - line_element.y1

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

        for page_layout in extract_pages(pdf_bytes):
            blocks = self._process_page(page_layout)
            document.append({
                "page": page_layout.pageid,
                "textAnnotations": blocks,
                "textPreview": " ".join(
                    word["text"]
                    for line in self.extract_text_lines(page_layout)
                    for word in line["words"]
                )
            })

        return document

    def _process_page(self, page_layout: LTPage) -> List[Dict[str, Any]]:
        """
        Process a single PDF page.

        :param page: PDF page object
        :param page_number: Current page number
        :return: List of text block dictionaries
        """

        # Create page block
        page_block = Block(
            block_type="PAGE",
            bounding_poly=BoundingPoly.from_bbox(
                (0, 0, page_layout.width, page_layout.height)),
            relationships=[{"type": "CHILD", "ids": []}]
        )

        line_blocks = []
        word_blocks = []

        # Process lines
        lines = self.extract_text_lines(page_layout)

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
            line_blocks.append(line_block)

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
                word_blocks.append(word_block)

        # Combine blocks
        blocks = []
        blocks.append(page_block)
        blocks.extend(line_blocks)
        blocks.extend(word_blocks)

        # Serialize blocks
        output_blocks = [block.to_dict() for block in blocks]

        return output_blocks
