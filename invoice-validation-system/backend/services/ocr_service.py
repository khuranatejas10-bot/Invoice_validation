import os
# Limit threads to 1 to prevent segmentation faults on macOS process exit/reload
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import logging
import threading
from typing import List, Dict, Any
import numpy as np
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

class ThreadSafePaddleOCR:
    """
    A thread-safe singleton wrapper around PaddleOCR.
    Since PaddlePaddle C++ core predictors are not thread-safe, all inferences
    and initialization are serialized using a reentrant threading lock.
    """
    _instance = None
    _init_lock = threading.Lock()
    _inference_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._init_lock:
                if not cls._instance:
                    cls._instance = super(ThreadSafePaddleOCR, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if already initialized
        if hasattr(self, "_initialized") and self._initialized:
            return
            
        self.ocr_engine = None
        self._initialized = True

    def get_engine(self) -> PaddleOCR:
        """Lazy-loads and initializes the PaddleOCR instance thread-safely."""
        if self.ocr_engine is None:
            with self._init_lock:
                if self.ocr_engine is None:
                    logger.info("Initializing PaddleOCR model (Lazy-loading)...")
                    try:
                        # Initialize PaddleOCR with English language and angle classification
                        self.ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
                        logger.info("PaddleOCR engine initialized successfully.")
                    except Exception as e:
                        logger.error(f"Failed to initialize PaddleOCR engine: {e}", exc_info=True)
                        raise RuntimeError(f"OCR Engine Initialization Failed: {e}")
        return self.ocr_engine

    def run_inference(self, image_path: str) -> List[Dict[str, Any]]:
        """Runs OCR inference on an image thread-safely using a serialization lock."""
        if not os.path.exists(image_path):
            logger.error(f"Image path does not exist for OCR: {image_path}")
            return []

        engine = self.get_engine()
        
        logger.info(f"Locking OCR service for inference on: {os.path.basename(image_path)}")
        with self._inference_lock:
            logger.info(f"Starting PaddleOCR inference on: {os.path.basename(image_path)}")
            try:
                result = engine.ocr(image_path)
                logger.info(f"Completed PaddleOCR inference on: {os.path.basename(image_path)}")
                return self._parse_ocr_result(result)
            except Exception as e:
                logger.error(f"Exception during PaddleOCR inference on {image_path}: {e}", exc_info=True)
                return []

    def _parse_ocr_result(self, result: Any) -> List[Dict[str, Any]]:
        """Parses raw PaddleOCR result structure into a standard coordinates block list."""
        extracted_blocks = []
        if not result or not isinstance(result, list) or len(result) == 0:
            return extracted_blocks

        first_res = result[0]
        if isinstance(first_res, dict):
            # PaddleX dict format support
            texts = first_res.get('rec_texts', [])
            boxes = first_res.get('rec_boxes', first_res.get('dt_polys', []))
            for text, box in zip(texts, boxes):
                flat_bbox = [0, 0, 0, 0]
                if len(box) == 4 and not isinstance(box[0], (list, tuple, np.ndarray)):
                    flat_bbox = [int(box[0]), int(box[1]), int(box[2]), int(box[3])]
                elif len(box) >= 4:
                    xs = [pt[0] for pt in box]
                    ys = [pt[1] for pt in box]
                    flat_bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
                extracted_blocks.append({
                    "text": text,
                    "bbox": flat_bbox
                })
        elif isinstance(first_res, list):
            # Standard list-of-lists format support
            for line in first_res:
                if isinstance(line, list) and len(line) >= 2:
                    bbox = line[0]
                    text = line[1][0]
                    xs = [pt[0] for pt in bbox]
                    ys = [pt[1] for pt in bbox]
                    flat_bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
                    extracted_blocks.append({
                        "text": text,
                        "bbox": flat_bbox
                    })
        return extracted_blocks

# Instantiate the singleton service
_ocr_service = ThreadSafePaddleOCR()

def get_ocr_instance() -> PaddleOCR:
    """Backward-compatible helper to get the raw singleton PaddleOCR engine."""
    return _ocr_service.get_engine()

def extract_text_from_image(image_path: str) -> List[Dict[str, Any]]:
    """Runs PaddleOCR inference on an image thread-safely and returns parsed blocks."""
    return _ocr_service.run_inference(image_path)
