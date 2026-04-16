import * as pdfjsLib from 'pdfjs-dist';

// @ts-ignore
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?worker';

// Create a worker instance and get its URL
const worker = new PdfWorker();
pdfjsLib.GlobalWorkerOptions.workerPort = worker;

export async function pdfToImages(
  file: File,
  options: { scale?: number; quality?: number; maxPages?: number } = {}
): Promise<string[]> {
  const { scale = 1.5, quality = 0.85, maxPages = 20 } = options;
  
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  
  const numPages = Math.min(pdf.numPages, maxPages);
  const images: string[] = [];
  
  for (let pageNum = 1; pageNum <= numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale });
    
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Failed to get canvas context');
    
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    
    await page.render({ canvasContext: context, viewport }).promise;
    images.push(canvas.toDataURL('image/jpeg', quality));
    page.cleanup();
  }
  
  return images;
}

export function isPDF(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
}

export async function processDocument(file: File): Promise<string[]> {
  if (isPDF(file)) {
    return pdfToImages(file);
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve([reader.result as string]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
