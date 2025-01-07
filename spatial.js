import { nanoid } from 'nanoid/non-secure';

function compactNumberString(str) {
  // Return the original string if alphabetical characters are present
  if (/[a-zA-Z]/.test(str)) {
    return str;
  }

  if (/\d/.test(str)) {
    // Remove all spaces if at least one digit is present and no alphabetical characters
    return str.replace(/\s/g, '');
  } else {
    // Return the original string if no digits are present
    return str;
  }
}

const getBoundingBoxOfPdfTextItem = (textItem) => {
  const [, , , , e, f] = textItem.transform;

  /**
   * We use correctFloatingPointError since FY21 ST Mark page 5 "4" value on "Loss on Dispposal"
   * row is returning false positive epsilon in the number causing the width to become 0.
   */
  const width = correctFloatingPointError(textItem.width);
  const height = correctFloatingPointError(textItem.height);

  // Bottom-left corner
  const x1 = e;
  const y1 = f;

  // Top-left corner
  const x2 = e;
  const y2 = f + height;

  // Bottom-right corner
  const x3 = e + width;
  const y3 = f;

  // Top-right corner
  const x4 = e + width;
  const y4 = f + height;

  return {
    bottomLeft: { x: x1, y: y1 },
    topLeft: { x: x2, y: y2 },
    bottomRight: { x: x3, y: y3 },
    topRight: { x: x4, y: y4 },
  };
};

const correctFloatingPointError = (value) => {
  // Convert the number to a string in exponential notation
  const str = value.toExponential();

  // Split the string into the coefficient and exponent parts
  const [coefficient, exponent] = str.split('e');

  // Parse the coefficient and exponent
  const parsedCoefficient = parseFloat(coefficient);
  const parsedExponent = parseInt(exponent);

  // If the exponent is negative and small, it's likely a representation error
  if (parsedExponent < -10) {
    // Return just the coefficient, rounded to 3 decimal places
    return Math.round(parsedCoefficient * 1000) / 1000;
  }

  // Otherwise, return the original value
  return value;
};

const convertBottomLeftBoudingBoxToTopLeft = (boundingBox, height) => {
  return {
    bottomLeft: {
      x: boundingBox.bottomLeft.x,
      y: height - boundingBox.bottomLeft.y,
    },
    topLeft: {
      x: boundingBox.topLeft.x,
      y: height - boundingBox.topLeft.y,
    },
    bottomRight: {
      x: boundingBox.bottomRight.x,
      y: height - boundingBox.bottomRight.y,
    },
    topRight: {
      x: boundingBox.topRight.x,
      y: height - boundingBox.topRight.y,
    },
  };
};

const parseTextBlockLine = (item, height) => {
  const lineBlock = parseTextBlock(item, height, 'LINE');
  const wordItems = splitItemIfNeeded(item);
  const blocks = wordItems.map((item) => parseTextBlock(item, height, 'WORD'));
  const blockIds = blocks.map((block) => block.id);
  lineBlock.relationships = [{ ids: [...blockIds], type: 'CHILD' }];

  return [lineBlock, blocks];
};

const splitItemIfNeeded = (item) => {
  // Check if the item contains numbers and no alphabetical characters
  if (!/\d/.test(item.str) || /[a-zA-Z]/.test(item.str)) {
    return [item];
  }

  const parts = item.str.trim().split(/\s+/);
  if (
    parts.length > 1 &&
    parts.every((part) =>
      /^\(?\s*-?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\s*\)?$/.test(part)
    )
  ) {
    let currentX = item.transform[4];
    const scale = item.transform[0];

    return parts.map((part, index) => {
      const trimmedPart = part.trim();
      const partWidth = trimmedPart.length * (scale / 2); // Estimate width based on scale
      const spacesBefore = item.str
        .slice(0, item.str.indexOf(part))
        .match(/\s+/g);
      const spacesWidth = spacesBefore
        ? spacesBefore.join('').length * (scale / 4)
        : 0; // Estimate space width

      currentX += spacesWidth;

      const newItem = {
        ...item,
        str: trimmedPart,
        width: partWidth,
        transform: [...item.transform.slice(0, 4), currentX, item.transform[5]],
      };

      currentX += partWidth;

      return newItem;
    });
  }
  return [item];
};

const parseTextBlock = (item, height, blockType) => {
  const boundingBox = getBoundingBoxOfPdfTextItem(item);
  const transformedBoundingBox = convertBottomLeftBoudingBoxToTopLeft(
    boundingBox,
    height
  );
  return {
    blockType: blockType,
    description: compactNumberString(item.str),
    boundingPoly: {
      vertices: [
        transformedBoundingBox.topLeft,
        transformedBoundingBox.topRight,
        transformedBoundingBox.bottomRight,
        transformedBoundingBox.bottomLeft,
      ],
    },
    id: nanoid(),
  };
};

const createPageBlock = (topLeft, bottomRight) => {
  return {
    blockType: 'PAGE',
    description: '',
    id: nanoid(),
    relationships: [
      {
        ids: [],
        type: 'CHILD',
      },
    ],
    boundingPoly: {
      vertices: [
        { x: topLeft.x, y: topLeft.y },
        { x: bottomRight.x, y: topLeft.y },
        { x: bottomRight.x, y: bottomRight.y },
        { x: topLeft.x, y: bottomRight.y },
      ],
    },
  };
};

const adjustTextCoordinates = (textItem, rotation, pageWidth, pageHeight) => {
  // Extract the current x, y position from the transformation matrix
  const [a, b, c, d, x, y] = textItem.transform;

  // Determine the new coordinates based on the rotation
  let newTransform;

  switch (rotation) {
    case 0:
      // No rotation, return the original transformation
      newTransform = [a, b, c, d, x, y];
      break;

    case 90:
      // Rotate 90 degrees clockwise: (x, y) => (y, pageWidth - x)
      newTransform = [a, b, c, d, y, pageWidth - x];
      break;

    case 180:
      // Rotate 180 degrees clockwise: (x, y) => (pageWidth - x, pageHeight - y)
      newTransform = [a, b, c, d, pageWidth - x, pageHeight - y];
      break;

    case 270:
      // Rotate 270 degrees clockwise: (x, y) => (pageHeight - y, x)
      newTransform = [a, b, c, d, pageHeight - y, x];
      break;

    default:
      throw new Error(
        'Invalid rotation value. Must be 0, 90, 180, or 270 degrees.'
      );
  }

  // Return a new text item with the updated transformation matrix
  return {
    ...textItem,
    transform: newTransform, // Replace the old transform with the new one
  };
};

const adjustViewBox = (rotation, pageWidth, pageHeight) => {
  let newViewBox;

  switch (rotation) {
    case 0:
      // No rotation, return the original viewBox
      newViewBox = [0, 0, pageWidth, pageHeight];
      break;

    case 90:
      // Rotate 90 degrees clockwise: swap width and height
      newViewBox = [0, 0, pageHeight, pageWidth];
      break;

    case 180:
      // Rotate 180 degrees: width and height remain the same, but you may adjust the origin
      newViewBox = [0, 0, pageWidth, pageHeight];
      break;

    case 270:
      // Rotate 270 degrees clockwise: swap width and height
      newViewBox = [0, 0, pageHeight, pageWidth];
      break;

    default:
      throw new Error(
        'Invalid rotation value. Must be 0, 90, 180, or 270 degrees.'
      );
  }

  return newViewBox;
};

export const mimicOcr = async (pdfProxy) => {
  const fakeOcr = [];

  const trimText = (text) => text.trim().replace(/\s+/g, ' ');

  const sortInReadingOrderFn = (a, b) => {
    const aTop = a.boundingPoly.vertices[0].y;
    const bTop = b.boundingPoly.vertices[0].y;
    const aLeft = a.boundingPoly.vertices[0].x;
    const bLeft = b.boundingPoly.vertices[0].x;

    // If blocks are close vertically, sort by horizontal position
    if (Math.abs(aTop - bTop) < 10) {
      return aLeft - bLeft;
    }
    // Otherwise, sort by vertical position
    return aTop - bTop;
  };

  for (let i = 1; i <= pdfProxy.numPages; i++) {
    const page = await pdfProxy.getPage(i);
    const { viewBox } = page.getViewport();
    if (viewBox.length < 4) throw new Error('Invalid PDF View Box');
    const adjustedViewBox = adjustViewBox(page.rotate, viewBox[2], viewBox[3]);
    const pageBlock = createPageBlock(
      { x: adjustedViewBox[0], y: adjustedViewBox[1] },
      { x: adjustedViewBox[2], y: adjustedViewBox[3] }
    );
    const textContent = await page.getTextContent();
    const filteredContent = textContent.items
      .filter((item) => 'str' in item)
      .filter((item) => trimText(item.str) !== '');
    console.log(filteredContent)
    const lineBlocks = [];
    const wordBlocks = [];
    const adjustedContent = filteredContent.map((item) =>
      adjustTextCoordinates(item, page.rotate, viewBox[2], viewBox[3])
    );
    for (const item of adjustedContent) {
      const [line, words] = parseTextBlockLine(item, adjustedViewBox[3]);
      lineBlocks.push(line);
      wordBlocks.push(...words);
    }
    const lineIds = lineBlocks.map((line) => line.id);
    pageBlock.relationships = [{ ids: [...lineIds], type: 'CHILD' }];

    // sort line and word blocks in reading order
    lineBlocks.sort(sortInReadingOrderFn);
    wordBlocks.sort(sortInReadingOrderFn);

    const all = [pageBlock, ...lineBlocks, ...wordBlocks];
    // const textPreview = text && i > 0 && i <= text.length ? text[i - 1] : '';
    const textPreview =
      filteredContent.map((item) => item.str).join(' ') + '\n';
    fakeOcr.push({
      textAnnotations: all,
      textPreview,
    });
  }
  return fakeOcr;
};
