"""
Multi-OCR Engine Adapter
รองรับ OneOCR, EasyOCR, PaddleOCR พร้อม fallback mechanism
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import numpy as np
from PIL import Image
import cv2

# OCR Engine imports
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

# OneOCR (Windows DLL) - Implement with actual DLL
try:
    import ctypes
    from ctypes import wintypes, Structure, byref, POINTER, c_ubyte
    ONECR_AVAILABLE = True
except ImportError:
    ONECR_AVAILABLE = False

logger = logging.getLogger(__name__)


# OneOCR Img structure
class Img(Structure):
    """OneOCR image structure"""
    _fields_ = [
        ('t', ctypes.c_int32),
        ('col', ctypes.c_int32),
        ('row', ctypes.c_int32),
        ('_unk', ctypes.c_int32),
        ('step', ctypes.c_int64),
        ('data_ptr', ctypes.c_int64),
    ]


class OCRResult:
    """Standardized OCR result format"""
    
    def __init__(self, text: str, confidence: float, bbox: List[List[int]], 
                 position: Optional[Dict[str, int]] = None):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        self.position = position or self._calculate_position()
    
    def _calculate_position(self) -> Dict[str, int]:
        """Calculate position from bounding box"""
        if not self.bbox:
            return {"x": 0, "y": 0, "width": 0, "height": 0}
        
        x_coords = [point[0] for point in self.bbox]
        y_coords = [point[1] for point in self.bbox]
        
        return {
            "x": min(x_coords),
            "y": min(y_coords),
            "width": max(x_coords) - min(x_coords),
            "height": max(y_coords) - min(y_coords)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "position": self.position
        }


class OneOCREngine:
    """OneOCR Engine wrapper (Windows DLL)"""
    
    def __init__(self, dll_path: str, model_path: str):
        self.dll_path = dll_path
        self.model_path = model_path
        self.initialized = False
        self.oneocr = None
        self.script_dir = None
        
    def initialize(self) -> bool:
        """Initialize OneOCR DLL"""
        try:
            if not ONECR_AVAILABLE:
                logger.error("OneOCR not available - ctypes not found")
                return False
            
            self.script_dir = os.path.abspath(os.path.dirname(__file__))
            
            # Resolve DLL and model paths (prefer provided config paths)
            oneocr_dll_path = os.path.abspath(self.dll_path) if self.dll_path else os.path.join(self.script_dir, "oneocr.dll")
            oneocr_model_path = os.path.abspath(self.model_path) if self.model_path else os.path.join(self.script_dir, "oneocr.onemodel")
            
            # Setup environment to include DLL directory
            dll_dir = os.path.dirname(oneocr_dll_path)
            try:
                os.environ["path"] = dll_dir + os.pathsep + os.environ.get("path", "")
            except Exception:
                pass
            
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            if hasattr(kernel32, "SetDllDirectoryW"):
                try:
                    kernel32.SetDllDirectoryW(dll_dir)
                except Exception:
                    pass
            
            # Load OneOCR DLL
            if not os.path.exists(oneocr_dll_path):
                logger.error(f"OneOCR DLL not found: {oneocr_dll_path}")
                return False
            
            self.oneocr = ctypes.WinDLL(oneocr_dll_path)
            
            # Define function prototypes
            self._setup_function_prototypes()
            
            self.initialized = True
            logger.info("OneOCR initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"OneOCR initialization failed: {e}")
            return False
    
    def _setup_function_prototypes(self):
        """Setup OneOCR function prototypes"""
        try:
            # CreateOcrInitOptions
            self.oneocr.CreateOcrInitOptions.argtypes = [ctypes.POINTER(ctypes.c_int64)]
            self.oneocr.CreateOcrInitOptions.restype = ctypes.c_int64
            
            # OcrInitOptionsSetUseModelDelayLoad
            self.oneocr.OcrInitOptionsSetUseModelDelayLoad.argtypes = [ctypes.c_int64, ctypes.c_char]
            self.oneocr.OcrInitOptionsSetUseModelDelayLoad.restype = ctypes.c_int64
            
            # CreateOcrPipeline
            self.oneocr.CreateOcrPipeline.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
            self.oneocr.CreateOcrPipeline.restype = ctypes.c_int64
            
            # CreateOcrProcessOptions
            self.oneocr.CreateOcrProcessOptions.argtypes = [ctypes.POINTER(ctypes.c_int64)]
            self.oneocr.CreateOcrProcessOptions.restype = ctypes.c_int64
            
            # OcrProcessOptionsSetMaxRecognitionLineCount
            self.oneocr.OcrProcessOptionsSetMaxRecognitionLineCount.argtypes = [ctypes.c_int64, ctypes.c_int64]
            self.oneocr.OcrProcessOptionsSetMaxRecognitionLineCount.restype = ctypes.c_int64
            
            # RunOcrPipeline
            self.oneocr.RunOcrPipeline.argtypes = [ctypes.c_int64, ctypes.POINTER(Img), ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
            self.oneocr.RunOcrPipeline.restype = ctypes.c_int64
            
            # GetOcrLineCount
            self.oneocr.GetOcrLineCount.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
            self.oneocr.GetOcrLineCount.restype = ctypes.c_int64
            
            # GetOcrLine
            self.oneocr.GetOcrLine.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
            self.oneocr.GetOcrLine.restype = ctypes.c_int64
            
            # GetOcrLineContent
            self.oneocr.GetOcrLineContent.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
            self.oneocr.GetOcrLineContent.restype = ctypes.c_int64
            
        except Exception as e:
            logger.error(f"Failed to setup OneOCR function prototypes: {e}")
            raise
    
    def _prepare_image(self, image: Union[str, np.ndarray]) -> Img:
        """Prepare image for OneOCR processing"""
        try:
            # Load image
            if isinstance(image, str):
                logger.info(f"Loading image: {image}")
                
                # Try multiple methods to load image
                img = None
                
                # Method 1: Direct cv2.imread
                try:
                    img = cv2.imread(image, cv2.IMREAD_UNCHANGED)
                    logger.info(f"Loaded image via cv2.imread: {img.shape if img is not None else 'None'}")
                except Exception as e:
                    logger.warning(f"cv2.imread failed: {e}")
                
                # Method 2: Read bytes and decode
                if img is None:
                    try:
                        with open(image, 'rb') as f:
                            img_bytes = bytearray(f.read())
                        nparr = np.asarray(img_bytes, dtype=np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
                        logger.info(f"Loaded image via bytes decode: {img.shape if img is not None else 'None'}")
                    except Exception as e:
                        logger.warning(f"Bytes decode failed: {e}")
                
                # Method 3: PIL to OpenCV
                if img is None:
                    try:
                        from PIL import Image
                        pil_img = Image.open(image)
                        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        logger.info(f"Loaded image via PIL: {img.shape if img is not None else 'None'}")
                    except Exception as e:
                        logger.warning(f"PIL loading failed: {e}")
                
            else:
                img = image.copy()
                logger.info(f"Using provided numpy array: {img.shape}")
            
            if img is None:
                raise ValueError("Could not load image with any method")
            
            logger.info(f"Final image shape: {img.shape}, dtype: {img.dtype}")
            
            # Convert to RGBA
            if len(img.shape) == 3:
                if img.shape[2] == 3:
                    img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                elif img.shape[2] == 4:
                    img_rgba = img
                else:
                    raise ValueError(f"Unsupported image channels: {img.shape[2]}")
            else:
                # Grayscale to RGBA
                img_rgba = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
            
            # Ensure data is contiguous and correct type
            img_rgba = np.ascontiguousarray(img_rgba, dtype=np.uint8)
            
            # Create Img structure
            rows, cols = img_rgba.shape[:2]
            channels = img_rgba.shape[2] if len(img_rgba.shape) > 2 else 1
            step = cols * channels
            
            # Get data pointer
            data_ptr = img_rgba.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
            
            img_struct = Img(
                t=3,  # Image type
                col=cols,
                row=rows,
                _unk=0,
                step=step,
                data_ptr=ctypes.cast(data_ptr, ctypes.c_void_p).value
            )
            
            logger.info(f"Created Img struct: rows={rows}, cols={cols}, channels={channels}, step={step}")
            return img_struct
            
        except Exception as e:
            logger.error(f"Failed to prepare image: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def recognize(self, image: Union[str, np.ndarray]) -> List[OCRResult]:
        """Recognize text using OneOCR"""
        if not self.initialized:
            if not self.initialize():
                return []
        
        try:
            # Prepare image
            img_struct = self._prepare_image(image)
            
            # Initialize variables
            ctx = ctypes.c_int64()
            pipeline = ctypes.c_int64()
            opt = ctypes.c_int64()
            instance = ctypes.c_int64()
            
            # Create initialization options
            res = self.oneocr.CreateOcrInitOptions(byref(ctx))
            if res != 0:
                raise Exception(f"CreateOcrInitOptions failed with code {res}")
            
            # Set model delay load
            res = self.oneocr.OcrInitOptionsSetUseModelDelayLoad(ctx, 0)
            if res != 0:
                raise Exception(f"OcrInitOptionsSetUseModelDelayLoad failed with code {res}")
            
            # Create OCR pipeline
            model_path = oneocr_model_path
            if not os.path.exists(model_path):
                raise Exception(f"OneOCR model not found: {model_path}")
            
            model_bytes = model_path.encode("utf-8")
            key_bytes = b"kj)TGtrK>f]b[Piow.gU+nC@s\"\"\"\"\"\"4"
            
            # Create string buffers
            model_buf = ctypes.create_string_buffer(model_bytes)
            key_buf = ctypes.create_string_buffer(key_bytes)
            
            res = self.oneocr.CreateOcrPipeline(
                ctypes.addressof(model_buf),
                ctypes.addressof(key_buf),
                ctx,
                byref(pipeline)
            )
            if res != 0:
                raise Exception(f"CreateOcrPipeline failed with code {res}")
            
            logger.info("OneOCR model loaded successfully")
            
            # Create process options
            res = self.oneocr.CreateOcrProcessOptions(byref(opt))
            if res != 0:
                raise Exception(f"CreateOcrProcessOptions failed with code {res}")
            
            # Set max recognition line count
            res = self.oneocr.OcrProcessOptionsSetMaxRecognitionLineCount(opt, 1000)
            if res != 0:
                raise Exception(f"OcrProcessOptionsSetMaxRecognitionLineCount failed with code {res}")
            
            # Run OCR pipeline
            logger.info("Running OneOCR pipeline...")
            res = self.oneocr.RunOcrPipeline(pipeline, byref(img_struct), opt, byref(instance))
            if res != 0:
                logger.error(f"RunOcrPipeline failed with code {res}")
                # Try to get more information about the error
                logger.error("This might be due to:")
                logger.error("1. Image format not supported by OneOCR")
                logger.error("2. Image size too large or too small")
                logger.error("3. OneOCR model compatibility issue")
                raise Exception(f"RunOcrPipeline failed with code {res}")
            
            logger.info("OneOCR pipeline executed successfully")
            
            # Get line count
            line_count = ctypes.c_int64()
            res = self.oneocr.GetOcrLineCount(instance, byref(line_count))
            if res != 0:
                logger.error(f"GetOcrLineCount failed with code {res}")
                raise Exception(f"GetOcrLineCount failed with code {res}")
            
            logger.info(f"OneOCR recognized {line_count.value} lines")
            
            # If no lines found, try to diagnose the issue
            if line_count.value == 0:
                logger.warning("OneOCR found 0 lines. This might indicate:")
                logger.warning("1. Image has no readable text")
                logger.warning("2. Text is too small or too blurry")
                logger.warning("3. Image format issue")
                logger.warning("4. OneOCR model needs different preprocessing")
                
                # Try to save a debug image to see what OneOCR is processing
                try:
                    debug_img = cv2.imread(image) if isinstance(image, str) else image
                    if debug_img is not None:
                        debug_path = "debug_oneocr_input.png"
                        cv2.imwrite(debug_path, debug_img)
                        logger.info(f"Saved debug image to: {debug_path}")
                except Exception as e:
                    logger.warning(f"Could not save debug image: {e}")
            
            # Extract results
            ocr_results = []
            for lci in range(line_count.value):
                line = ctypes.c_int64()
                res = self.oneocr.GetOcrLine(instance, lci, byref(line))
                if res != 0 or line.value == 0:
                    continue
                
                # Get line content
                line_content = ctypes.c_int64()
                res = self.oneocr.GetOcrLineContent(line, byref(line_content))
                if res == 0 and line_content.value != 0:
                    content = ctypes.c_char_p(line_content.value).value.decode('utf-8', errors='ignore')
                    
                    # Create OCR result (OneOCR doesn't provide bbox, so we create a placeholder)
                    # In a real implementation, you might need additional OneOCR functions to get bbox
                    ocr_result = OCRResult(
                        text=content.strip(),
                        confidence=0.95,  # OneOCR doesn't provide confidence, using high default
                        bbox=[[0, lci*20], [len(content)*10, lci*20], [len(content)*10, (lci+1)*20], [0, (lci+1)*20]],
                        position={"x": 0, "y": lci*20, "width": len(content)*10, "height": 20}
                    )
                    ocr_results.append(ocr_result)
            
            logger.info(f"OneOCR extracted {len(ocr_results)} text blocks")
            return ocr_results
            
        except Exception as e:
            logger.error(f"OneOCR recognition failed: {e}")
            return []


class EasyOCREngine:
    """EasyOCR Engine wrapper"""
    
    def __init__(self, languages: List[str] = None, gpu: bool = False, model_storage_directory: Optional[str] = None, offline_only: bool = False):
        self.languages = languages or ['en']
        self.gpu = gpu
        self.model_storage_directory = model_storage_directory
        self.offline_only = offline_only
        self.reader = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize EasyOCR"""
        try:
            if not EASYOCR_AVAILABLE:
                logger.error("EasyOCR not available")
                return False
            
            # If offline_only is set, ensure model files are present locally
            if self.offline_only and self.model_storage_directory:
                try:
                    msd = os.path.abspath(self.model_storage_directory)
                    if not os.path.exists(msd):
                        logger.error(f"EasyOCR offline-only: model_storage_directory missing: {msd}")
                        return False
                except Exception:
                    logger.error("EasyOCR offline-only: invalid model_storage_directory")
                    return False

            # Initialize reader; if model_storage_directory is provided, use it
            if self.model_storage_directory:
                self.reader = easyocr.Reader(self.languages, gpu=self.gpu, model_storage_directory=self.model_storage_directory)
            else:
                self.reader = easyocr.Reader(self.languages, gpu=self.gpu)
            self.initialized = True
            logger.info(f"EasyOCR initialized with languages: {self.languages}")
            return True
        except Exception as e:
            logger.error(f"EasyOCR initialization failed: {e}")
            return False
    
    def recognize(self, image: Union[str, np.ndarray]) -> List[OCRResult]:
        """Recognize text using EasyOCR"""
        if not self.initialized:
            if not self.initialize():
                return []
        
        try:
            results = self.reader.readtext(image)
            ocr_results = []
            
            for (bbox, text, confidence) in results:
                # Convert bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                bbox_points = [[int(point[0]), int(point[1])] for point in bbox]
                ocr_results.append(OCRResult(text, confidence, bbox_points))
            
            logger.info(f"EasyOCR recognized {len(ocr_results)} text blocks")
            return ocr_results
            
        except Exception as e:
            logger.error(f"EasyOCR recognition failed: {e}")
            return []


class PaddleOCREngine:
    """PaddleOCR Engine wrapper"""
    
    def __init__(self, use_angle_cls: bool = True, use_gpu: bool = False,
                 det_model_dir: Optional[str] = None,
                 rec_model_dir: Optional[str] = None,
                 cls_model_dir: Optional[str] = None,
                 rec_char_dict_path: Optional[str] = None,
                 lang: Optional[str] = 'en',
                 offline_only: bool = False):
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self.det_model_dir = det_model_dir
        self.rec_model_dir = rec_model_dir
        self.cls_model_dir = cls_model_dir
        self.rec_char_dict_path = rec_char_dict_path
        self.lang = lang or 'en'
        self.offline_only = offline_only
        self.ocr = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize PaddleOCR"""
        try:
            if not PADDLEOCR_AVAILABLE:
                logger.error("PaddleOCR not available")
                return False
            
            # In offline-only mode, enforce local model directories
            if self.offline_only:
                required = [self.det_model_dir, self.rec_model_dir]
                missing = [p for p in required if not p or not os.path.exists(os.path.abspath(p))]
                if missing:
                    logger.error(f"PaddleOCR offline-only: missing local model dirs: {missing}")
                    return False

            kwargs = {
                'use_angle_cls': self.use_angle_cls,
                'use_gpu': self.use_gpu,
                'lang': self.lang
            }
            if self.det_model_dir:
                kwargs['det_model_dir'] = self.det_model_dir
            if self.rec_model_dir:
                kwargs['rec_model_dir'] = self.rec_model_dir
            if self.cls_model_dir:
                kwargs['cls_model_dir'] = self.cls_model_dir
            if self.rec_char_dict_path:
                kwargs['rec_char_dict_path'] = self.rec_char_dict_path

            self.ocr = PaddleOCR(**kwargs)
            self.initialized = True
            logger.info("PaddleOCR initialized")
            return True
        except Exception as e:
            logger.error(f"PaddleOCR initialization failed: {e}")
            return False
    
    def recognize(self, image: Union[str, np.ndarray]) -> List[OCRResult]:
        """Recognize text using PaddleOCR"""
        if not self.initialized:
            if not self.initialize():
                return []
        
        try:
            results = self.ocr.ocr(image, cls=self.use_angle_cls)
            ocr_results = []
            
            if results and results[0]:
                for line in results[0]:
                    if line:
                        bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        text_info = line[1]
                        text = text_info[0]
                        confidence = text_info[1]
                        
                        bbox_points = [[int(point[0]), int(point[1])] for point in bbox]
                        ocr_results.append(OCRResult(text, confidence, bbox_points))
            
            logger.info(f"PaddleOCR recognized {len(ocr_results)} text blocks")
            return ocr_results
            
        except Exception as e:
            logger.error(f"PaddleOCR recognition failed: {e}")
            return []


class MultiOCRManager:
    """Multi-engine OCR Manager with fallback support"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engines = {}
        self.engine_order = []
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available OCR engines based on config"""
        ocr_config = self.config.get('ocr', {})
        engines_config = ocr_config.get('engines', {})
        offline_only = ocr_config.get('offline_only', False)
        
        # OneOCR (always local-only)
        if engines_config.get('oneocr', {}).get('enabled', False) and ONECR_AVAILABLE:
            oneocr_config = engines_config['oneocr']
            dll_path = oneocr_config.get('dll_path', './oneocr.dll')
            model_path = oneocr_config.get('model_path', './oneocr.onemodel')
            # If offline_only, verify local files exist; otherwise skip
            if offline_only:
                if not (dll_path and os.path.exists(os.path.abspath(dll_path)) and model_path and os.path.exists(os.path.abspath(model_path))):
                    logger.warning(f"OneOCR offline-only: missing dll or model at {dll_path}, {model_path}; engine disabled")
                else:
                    self.engines['oneocr'] = OneOCREngine(dll_path=dll_path, model_path=model_path)
            else:
                self.engines['oneocr'] = OneOCREngine(dll_path=dll_path, model_path=model_path)
        
        # EasyOCR
        if engines_config.get('easyocr', {}).get('enabled', False) and EASYOCR_AVAILABLE:
            easyocr_config = engines_config['easyocr']
            msd = easyocr_config.get('model_storage_directory')
            if offline_only and not msd:
                logger.warning("EasyOCR offline-only: no local model_storage_directory configured; engine disabled")
            else:
                self.engines['easyocr'] = EasyOCREngine(
                    languages=easyocr_config.get('languages', ['en']),
                    gpu=easyocr_config.get('gpu', False),
                    model_storage_directory=msd,
                    offline_only=offline_only
                )
        
        # PaddleOCR
        if engines_config.get('paddleocr', {}).get('enabled', False) and PADDLEOCR_AVAILABLE:
            paddleocr_config = engines_config['paddleocr']
            det_dir = paddleocr_config.get('det_model_dir')
            rec_dir = paddleocr_config.get('rec_model_dir')
            cls_dir = paddleocr_config.get('cls_model_dir')
            lang = paddleocr_config.get('lang', 'en')
            rec_dict = paddleocr_config.get('rec_char_dict_path')
            if offline_only and not (det_dir and rec_dir):
                logger.warning("PaddleOCR offline-only: local det_model_dir/rec_model_dir not configured; engine disabled")
            else:
                self.engines['paddleocr'] = PaddleOCREngine(
                    use_angle_cls=paddleocr_config.get('use_angle_cls', True),
                    use_gpu=paddleocr_config.get('use_gpu', False),
                    det_model_dir=det_dir,
                    rec_model_dir=rec_dir,
                    cls_model_dir=cls_dir,
                    rec_char_dict_path=rec_dict,
                    lang=lang,
                    offline_only=offline_only
                )
        
        # Sort engines by priority
        self.engine_order = sorted(
            self.engines.keys(),
            key=lambda x: engines_config.get(x, {}).get('priority', 999)
        )
        
        logger.info(f"Initialized OCR engines: {self.engine_order}")
    
    def _preprocess_image(self, image: Union[str, np.ndarray]) -> np.ndarray:
        """Preprocess image for better OCR results"""
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image.copy()
        
        if img is None:
            raise ValueError("Could not load image")
        
        # Convert to RGB if needed
        if len(img.shape) == 3 and img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Apply preprocessing if enabled
        preprocessing = self.config.get('ocr', {}).get('preprocessing', {})
        
        if preprocessing.get('denoise', False):
            img = cv2.medianBlur(img, 3)
        
        if preprocessing.get('enhance', False):
            # Enhance contrast
            lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            img = cv2.merge([l, a, b])
            img = cv2.cvtColor(img, cv2.COLOR_LAB2RGB)
        
        return img
    
    def recognize(self, image: Union[str, np.ndarray], 
                 engine: Optional[str] = None) -> List[OCRResult]:
        """
        Recognize text using specified engine or auto-fallback
        
        Args:
            image: Image path or numpy array
            engine: Specific engine to use (optional)
        
        Returns:
            List of OCRResult objects
        """
        try:
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Use specific engine if requested
            if engine and engine in self.engines:
                results = self.engines[engine].recognize(processed_image)
                if results:
                    logger.info(f"Successfully recognized with {engine}")
                    return results
                else:
                    logger.warning(f"{engine} returned no results, trying fallback")
            
            # Try engines in priority order
            for engine_name in self.engine_order:
                if engine and engine_name != engine:
                    continue
                
                logger.info(f"Trying {engine_name}...")
                results = self.engines[engine_name].recognize(processed_image)
                
                if results:
                    logger.info(f"Successfully recognized with {engine_name}")
                    return results
                else:
                    logger.warning(f"{engine_name} returned no results")
            
            logger.error("All OCR engines failed")
            return []
            
        except Exception as e:
            logger.error(f"OCR recognition failed: {e}")
            return []
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines"""
        return list(self.engines.keys())
    
    def extract_text(self, image: Union[str, np.ndarray],
                     engine: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from image with standardized output format

        Args:
            image: Image path or numpy array
            engine: Specific engine to use (optional)

        Returns:
            Dict with 'success', 'text', 'engine', 'confidence', 'details'
        """
        try:
            # Get OCR results
            ocr_results = self.recognize(image, engine)

            if not ocr_results:
                return {
                    'success': False,
                    'error': 'No text recognized',
                    'engine': engine or 'auto',
                    'confidence': 0.0
                }

            # Sort by position (top to bottom, left to right)
            sorted_results = sorted(ocr_results, key=lambda x: (x.position['y'], x.position['x']))

            # Combine text
            text_blocks = []
            total_confidence = 0.0

            for result in sorted_results:
                text_blocks.append(result.text)
                total_confidence += result.confidence

            combined_text = '\n'.join(text_blocks)
            avg_confidence = total_confidence / len(ocr_results) if ocr_results else 0.0

            # Determine which engine was used
            used_engine = engine
            if not engine:
                # Find which engine succeeded
                for engine_name in self.engine_order:
                    if engine_name in self.engines:
                        test_results = self.engines[engine_name].recognize(image)
                        if test_results:
                            used_engine = engine_name
                            break
                used_engine = used_engine or 'auto'

            return {
                'success': True,
                'text': combined_text,
                'engine': used_engine,
                'confidence': avg_confidence,
                'details': {
                    'text_blocks': len(text_blocks),
                    'total_chars': len(combined_text)
                }
            }

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'engine': engine or 'auto',
                'confidence': 0.0
            }

    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about available engines"""
        info = {}
        for name, engine in self.engines.items():
            info[name] = {
                'available': True,
                'initialized': engine.initialized,
                'type': type(engine).__name__
            }
        return info


# Example usage and testing
if __name__ == "__main__":
    import json
    
    # Load config
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize OCR manager
    ocr_manager = MultiOCRManager(config)
    
    print("Available engines:", ocr_manager.get_available_engines())
    print("Engine info:", ocr_manager.get_engine_info())
    
    # Test with sample image (if available)
    test_image = "test_image.jpg"
    if os.path.exists(test_image):
        results = ocr_manager.recognize(test_image)
        print(f"Recognition results: {len(results)} text blocks found")
        for result in results[:3]:  # Show first 3 results
            print(f"Text: {result.text}, Confidence: {result.confidence:.2f}")
    else:
        print("No test image found. Please add a test image to test recognition.")

