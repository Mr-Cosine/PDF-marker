pyinstaller --onedir --name=PDFmarkerExecutable `
            --specpath PDFmarkerApp_tesseractOCR/info `
            --workpath PDFmarkerApp_tesseractOCR/info/build `
            --distpath PDFmarkerApp_tesseractOCR `
            --collect-all cv2 `
            --hidden-import pytesseract `
            --hidden-import pymupdf `
            --hidden-import numpy `
            --hidden-import cv2 `
            --hidden-import PIL `
            --hidden-import paddleOCR_reader `
            --hidden-import tesseractOCR_reader `
            --add-data "D:\Coding_projects\Work automations\NV request marker\OCRmodels\TesseractOCR;OCRmodels\TesseractOCR" `
tesseractOCR_PDFmarker.py