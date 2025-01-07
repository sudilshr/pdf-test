import { parseTextVisibility } from './utils.js';
import { mimicOcr } from './spatial.js';

const canvas = document.getElementById('pdf-canvas');
const ctx = canvas.getContext('2d');
const fileInput = document.getElementById('fileInput');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageInfo = document.getElementById('page-info');
const extractorSelect = document.getElementById('extractor');
const blockTypeSelect = document.getElementById('block-type');

let pdfDoc = null;
let currentPage = 1;
let totalPages = 0;
let ocrData = null;
let selectedExtractor = extractorSelect.value;
let selectedBlockType = blockTypeSelect.value;

// Disable the page navigation buttons initially
prevPageBtn.disabled = true;
nextPageBtn.disabled = true;

// Listen for file input changes
fileInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (file && file.type === 'application/pdf') {
    loadPdf(file);
  }
});

extractorSelect.addEventListener('change', (event) => {
  selectedExtractor = event.target.value;
  loadPageAndText(currentPage);
});

blockTypeSelect.addEventListener('change', (event) => {
  selectedBlockType = event.target.value;
  loadPageAndText(currentPage);
});

// Load "mytables.pdf" by default on page load
window.addEventListener('load', () => {
  fetch('mytables.pdf')
    .then((response) => response.blob())
    .then((blob) => {
      const file = new File([blob], 'mytables.pdf', {
        type: 'application/pdf',
      });
      loadPdf(file);
    });
});

function updatePageInfo() {
  pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  prevPageBtn.disabled = currentPage === 1;
  nextPageBtn.disabled = currentPage === totalPages;
}

// Listen for page navigation button clicks
prevPageBtn.addEventListener('click', () => {
  if (currentPage > 1) {
    currentPage--;
    loadPageAndText(currentPage);
    updatePageInfo();
  }
});

nextPageBtn.addEventListener('click', () => {
  if (currentPage < totalPages) {
    currentPage++;
    loadPageAndText(currentPage);
    updatePageInfo();
  }
});

// Function to load PDF from a file
function loadPdf(file) {
  const fileReader = new FileReader();

  // Read the selected file as an ArrayBuffer
  fileReader.onload = async function () {
    const typedarray = new Uint8Array(this.result);

    ocrData = await extractPdf(typedarray);

    // Load PDF from the ArrayBuffer
    pdfjsLib.disableWorker = true;
    pdfjsLib.getDocument(typedarray).promise.then((pdf) => {
      pdfDoc = pdf;
      totalPages = pdf.numPages;
      currentPage = 1;
      updatePageInfo();
      loadPageAndText(currentPage);
    });
  };

  fileReader.readAsArrayBuffer(file);
}

async function extractPdf(typedarray) {
  // # File Upload
  // curl -F "file=@document.pdf" http://localhost:5000/extract
  // # Base64 JSON
  // curl -X POST -H "Content-Type: application/json"          -d '{"pdf_base64":"base64_encoded_pdf_content"}'          http://localhost:5000/extract

  const data = {
    pdfplumber: [],
    pymupdf: [],
    pdfminer: [],
    pdfjs: [],
  };
  const base64 = btoa(
    typedarray.reduce((data, byte) => data + String.fromCharCode(byte), '')
  );
  
  // console.time('extract:pdfplumber');
  // const res = await fetch('http://localhost:5000/extract', {
  //   method: 'POST',
  //   headers: {
  //     'Content-Type': 'application/json',
  //   },
  //   body: JSON.stringify({
  //     pdf_base64: base64,
  //     extractor: 'pdfplumber',
  //   }),
  // });
  // data.pdfplumber = await res.json();
  // console.timeEnd('extract:pdfplumber');

  // console.time('extract:pymupdf');
  // const res2 = await fetch('http://localhost:5000/extract', {
  //   method: 'POST',
  //   headers: {
  //     'Content-Type': 'application/json',
  //   },
  //   body: JSON.stringify({
  //     pdf_base64: base64,
  //     extractor: 'pymupdf',
  //   }),
  // });
  // data.pymupdf = await res2.json();
  // console.timeEnd('extract:pymupdf');

  console.time('extract:pdfminer');
  const res3 = await fetch('http://localhost:5000/extract', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      pdf_base64: base64,
      extractor: 'pdfminer',
    }),
  });
  data.pdfminer = await res3.json();
  console.timeEnd('extract:pdfminer');

  console.time('extract:pdfjs');
  pdfjsLib.disableWorker = true;
  const pdfDoc = await pdfjsLib.getDocument(typedarray).promise;
  data.pdfjs = await mimicOcr(pdfDoc);
  console.timeEnd('extract:pdfjs');

  console.log('data', data);

  return data;
}

function loadPageAndText(pageNum) {
  // Fetch the specified page
  pdfDoc.getPage(pageNum).then(async (page) => {
    const viewport = page.getViewport({ scale: 1 });
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    const pdfCanvas = document.getElementById('pdf-canvas');
    /** @type {CanvasRenderingContext2D} */
    const pdfCtx = pdfCanvas.getContext('2d');

    // Render the PDF page into canvas context
    const renderContext = {
      canvasContext: pdfCtx,
      viewport: viewport,
    };
    await page.render(renderContext).promise;

    // const { items } = await page.getTextContent();
    // console.log('items', items);

    // const fakeOcr = await mimicOcr(pdfDoc);

    const fakeOcr = ocrData[selectedExtractor];

    const blocks = fakeOcr[pageNum - 1].textAnnotations;

    // add border to pdf canvas
    pdfCtx.strokeStyle = 'gray';
    pdfCtx.lineWidth = 2;
    pdfCtx.strokeRect(0, 0, pdfCanvas.width, pdfCanvas.height);

    // Render text on the second canvas at the exact position
    // check for null and undefined as well
    // blocks
    //   .filter((block) => block.blockType === 'WORD')
    //   .forEach((word) => {
    //     const {
    //       description,
    //       boundingPoly: { vertices },
    //     } = word;
    //     const x = vertices[0].x;
    //     const y = vertices[0].y;
    //     const width = vertices[1].x - vertices[0].x;
    //     const height = vertices[2].y - vertices[0].y;
    //     pdfCtx.font = `8px sans-serif`;
    //     pdfCtx.fillStyle = 'red';
    //     pdfCtx.fillText(description, x, y);

    //     // draw bounding box
    //     // assign random color
    //     const color = `#${Math.floor(Math.random() * 16777215).toString(16)}`;
    //     pdfCtx.strokeStyle = color;
    //     pdfCtx.lineWidth = 1;
    //     pdfCtx.strokeRect(x, y, width, height);
    //   });

    const RENDER_MODE = selectedBlockType; // LINE, WORD
    const lineBlocks = blocks.filter((block) => block.blockType === 'LINE');
    const relationshipIds = lineBlocks.flatMap((line) =>
      line.relationships && line.relationships.length
        ? line.relationships[0].ids
        : []
    );

    const wordBlocks = blocks.filter((block) => block.blockType === 'WORD');
    const renderBlocks =
      RENDER_MODE === 'WORD'
        ? wordBlocks.filter((word) => relationshipIds.includes(word.id))
        : lineBlocks;
    renderBlocks.forEach((word) => {
      const {
        description,
        boundingPoly: { vertices },
      } = word;
      const x = vertices[0].x;
      const y = vertices[0].y;
      const width = vertices[1].x - vertices[0].x;
      const height = vertices[2].y - vertices[0].y;
      pdfCtx.font = `8px sans-serif`;
      pdfCtx.fillStyle = 'red';
      pdfCtx.fillText(description, x, y);

      // draw bounding box
      // assign random color
      // const color = `#${Math.floor(Math.random() * 16777215).toString(16)}`;
      const color = 'blue';
      pdfCtx.strokeStyle = color;
      pdfCtx.lineWidth = 1;
      pdfCtx.strokeRect(x, y, width, height);
    });
  });
}
