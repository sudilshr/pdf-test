import { parseColors } from './color.js';

const canvas = document.getElementById('pdf-canvas');
const ctx = canvas.getContext('2d');
const fileInput = document.getElementById('fileInput');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageInfo = document.getElementById('page-info');

let pdfDoc = null;
let currentPage = 1;
let totalPages = 0;

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

// Load "hidden-text.pdf" by default on page load
window.addEventListener('load', () => {
  fetch('hidden-text.pdf')
    .then((response) => response.blob())
    .then((blob) => {
      const file = new File([blob], 'hidden-text.pdf', {
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
  fileReader.onload = function () {
    const typedarray = new Uint8Array(this.result);

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

function loadPageAndText(pageNum) {
  // Fetch the specified page
  pdfDoc.getPage(pageNum).then((page) => {
    const viewport = page.getViewport({ scale: 1 });
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    const pdfCanvas = document.getElementById('pdf-canvas');
    /** @type {CanvasRenderingContext2D} */
    const pdfCtx = pdfCanvas.getContext('2d');

    // Get the second canvas context
    const textCanvas = document.getElementById('text-canvas');
    /** @type {CanvasRenderingContext2D} */
    const textCtx = textCanvas.getContext('2d');

    // Render the PDF page into canvas context
    const renderContext = {
      canvasContext: pdfCtx,
      viewport: viewport,
    };
    page.render(renderContext);

    // Extract text content from the page
    page.getTextContent().then((textContent) => {
      // Set the canvas dimensions to match the PDF page
      textCanvas.width = viewport.width;
      textCanvas.height = viewport.height;

      // Clear the text canvas
      textCtx.clearRect(0, 0, textCanvas.width, textCanvas.height);

      // add border to pdf canvas
      pdfCtx.strokeStyle = 'gray';
      pdfCtx.lineWidth = 2;
      pdfCtx.strokeRect(0, 0, pdfCanvas.width, pdfCanvas.height);

      // add border to text canvas
      textCtx.strokeStyle = 'gray';
      textCtx.lineWidth = 2;
      textCtx.strokeRect(0, 0, textCanvas.width, textCanvas.height);

      let texts = textContent.items;
      console.time('color');
      parseColors(
        pdfCtx.getImageData(0, 0, viewport.width, viewport.height),
        textContent.items
      );
      console.timeEnd('color');
      console.log(texts);

      // Render text on the second canvas at the exact position
      texts.forEach((text) => {
        const { str, transform, width, height, color } = text;
        const x = transform[4];
        const y = viewport.height - transform[5];
        textCtx.font = `${height}px sans-serif`;
        textCtx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        textCtx.fillText(str, x, y);
      });

      // Update text output
      let text = '';
      textContent.items.forEach((item) => {
        text += item.str + '\n';
      });
    });
  });
}
