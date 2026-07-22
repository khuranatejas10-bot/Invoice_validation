import cv2
import numpy as np
import fitz  # PyMuPDF
from PIL import Image
import os

def pdf_to_images(pdf_path: str, output_dir: str) -> list[str]:
    """Convert a PDF file to a list of image paths using PyMuPDF."""
    doc = fitz.open(pdf_path)
    image_paths = []
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # 300 DPI is approx zoom factor of 300/72 = 4.16. We use 2.0 for 144 DPI as a good balance for OCR
        zoom = 2.0 
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        img_path = os.path.join(output_dir, f"{base_name}_page_{page_num}.png")
        pix.save(img_path)
        image_paths.append(img_path)
        
    return image_paths

def preprocess_image(image_path: str) -> str:
    """Apply series of OpenCV preprocessing techniques to improve OCR."""
    img = cv2.imread(image_path)
    if img is None:
        return image_path
        
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Deskew
    gray = deskew_image(gray)
    
    # Enhance Contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Sharpen
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    gray = cv2.filter2D(gray, -1, kernel)
    
    # Save processed image back
    processed_path = image_path.replace(".png", "_processed.png")
    cv2.imwrite(processed_path, gray)
    
    return processed_path

def deskew_image(image):
    """Detect and correct skew in the image."""
    # Thresholding
    thresh = cv2.bitwise_not(cv2.threshold(image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1])
    
    # Get coordinates of all non-zero pixels
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return image
        
    angle = cv2.minAreaRect(coords)[-1]
    
    # Handle angle based on OpenCV version
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # If the angle is very small, skip deskew
    if abs(angle) < 0.5:
        return image
        
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated
