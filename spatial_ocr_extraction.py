"""
Spatial OCR Analysis and Layout Detection
วิเคราะห์ spatial relationships ของข้อความจาก OCR results
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import cv2

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Text block with spatial information"""
    text: str
    confidence: float
    bbox: List[List[int]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    position: Dict[str, int]  # {x, y, width, height}
    center: Tuple[int, int]  # (center_x, center_y)


@dataclass
class Line:
    """Line containing multiple text blocks"""
    blocks: List[TextBlock]
    y_position: float
    height: float
    text: str


@dataclass
class Column:
    """Column containing multiple text blocks"""
    blocks: List[TextBlock]
    x_position: float
    width: float


@dataclass
class Table:
    """Table structure"""
    rows: List[List[TextBlock]]
    headers: List[TextBlock]
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)


class SpatialOCRAnalyzer:
    """Spatial analysis of OCR results"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.spatial_config = config.get('spatial_analysis', {})
        
        # Thresholds
        self.line_threshold = self.spatial_config.get('line_threshold', 20)
        self.column_threshold = self.spatial_config.get('column_threshold', 50)
        
        # Table detection
        self.table_config = self.spatial_config.get('table_detection', {})
        self.table_enabled = self.table_config.get('enabled', True)
        self.min_cells = self.table_config.get('min_cells', 4)
        self.min_rows = self.table_config.get('min_rows', 2)
        
        # Visualization
        self.viz_config = self.spatial_config.get('visualization', {})
        self.viz_enabled = self.viz_config.get('enabled', True)
        self.output_dir = self.viz_config.get('output_dir', './output/visualizations')
        
        self.text_blocks: List[TextBlock] = []
        self.lines: List[Line] = []
        self.columns: List[Column] = []
        self.tables: List[Table] = []
    
    def _ocr_result_to_text_block(self, ocr_result: Dict[str, Any]) -> TextBlock:
        """Convert OCR result to TextBlock"""
        bbox = ocr_result.get('bbox', [])
        position = ocr_result.get('position', {})
        
        # Calculate center point
        if bbox:
            center_x = sum(point[0] for point in bbox) // len(bbox)
            center_y = sum(point[1] for point in bbox) // len(bbox)
            center = (center_x, center_y)
        else:
            center = (position.get('x', 0), position.get('y', 0))
        
        return TextBlock(
            text=ocr_result.get('text', ''),
            confidence=ocr_result.get('confidence', 0.0),
            bbox=bbox,
            position=position,
            center=center
        )
    
    def load_ocr_results(self, ocr_results: List[Any]):
        """Load OCR results for analysis"""
        # Convert OCRResult objects to dictionaries if needed
        dict_results = []
        for result in ocr_results:
            if hasattr(result, 'to_dict'):
                dict_results.append(result.to_dict())
            else:
                dict_results.append(result)
        
        self.text_blocks = [self._ocr_result_to_text_block(result) for result in dict_results]
        logger.info(f"Loaded {len(self.text_blocks)} text blocks for analysis")
        
        # Perform analysis
        self._analyze_lines()
        self._analyze_columns()
        
        if self.table_enabled:
            self._detect_tables()
    
    def _analyze_lines(self):
        """Group text blocks into lines based on y-coordinate"""
        if not self.text_blocks:
            return
        
        # Sort by y position
        sorted_blocks = sorted(self.text_blocks, key=lambda b: b.position['y'])
        
        self.lines = []
        current_line = [sorted_blocks[0]]
        current_y = sorted_blocks[0].position['y']
        
        for block in sorted_blocks[1:]:
            y_diff = abs(block.position['y'] - current_y)
            
            if y_diff <= self.line_threshold:
                # Same line
                current_line.append(block)
                # Update average y position
                current_y = sum(b.position['y'] for b in current_line) / len(current_line)
            else:
                # New line
                if current_line:
                    self._create_line(current_line)
                current_line = [block]
                current_y = block.position['y']
        
        # Add last line
        if current_line:
            self._create_line(current_line)
        
        logger.info(f"Detected {len(self.lines)} lines")
    
    def _create_line(self, blocks: List[TextBlock]):
        """Create a Line object from text blocks"""
        # Sort blocks in line by x position
        blocks.sort(key=lambda b: b.position['x'])
        
        y_positions = [b.position['y'] for b in blocks]
        heights = [b.position['height'] for b in blocks]
        
        line = Line(
            blocks=blocks,
            y_position=sum(y_positions) / len(y_positions),
            height=max(heights),
            text=' '.join(block.text for block in blocks)
        )
        
        self.lines.append(line)
    
    def _analyze_columns(self):
        """Group text blocks into columns based on x-coordinate"""
        if not self.text_blocks:
            return
        
        # Sort by x position
        sorted_blocks = sorted(self.text_blocks, key=lambda b: b.position['x'])
        
        self.columns = []
        current_column = [sorted_blocks[0]]
        current_x = sorted_blocks[0].position['x']
        
        for block in sorted_blocks[1:]:
            x_diff = abs(block.position['x'] - current_x)
            
            if x_diff <= self.column_threshold:
                # Same column
                current_column.append(block)
                # Update average x position
                current_x = sum(b.position['x'] for b in current_column) / len(current_column)
            else:
                # New column
                if current_column:
                    self._create_column(current_column)
                current_column = [block]
                current_x = block.position['x']
        
        # Add last column
        if current_column:
            self._create_column(current_column)
        
        logger.info(f"Detected {len(self.columns)} columns")
    
    def _create_column(self, blocks: List[TextBlock]):
        """Create a Column object from text blocks"""
        # Sort blocks in column by y position
        blocks.sort(key=lambda b: b.position['y'])
        
        x_positions = [b.position['x'] for b in blocks]
        widths = [b.position['width'] for b in blocks]
        
        column = Column(
            blocks=blocks,
            x_position=sum(x_positions) / len(x_positions),
            width=max(widths)
        )
        
        self.columns.append(column)
    
    def _detect_tables(self):
        """Detect table structures"""
        if len(self.text_blocks) < self.min_cells:
            return
        
        # Simple table detection based on alignment
        # Look for blocks that form grid-like structures
        
        # Group blocks by approximate y positions (rows)
        row_groups = defaultdict(list)
        for block in self.text_blocks:
            # Find closest row group
            closest_row = None
            min_distance = float('inf')
            
            for row_y in row_groups.keys():
                distance = abs(block.position['y'] - row_y)
                if distance < min_distance and distance <= self.line_threshold:
                    min_distance = distance
                    closest_row = row_y
            
            if closest_row is not None:
                row_groups[closest_row].append(block)
            else:
                row_groups[block.position['y']].append(block)
        
        # Filter rows with sufficient blocks
        valid_rows = []
        for row_y, blocks in row_groups.items():
            if len(blocks) >= 2:  # At least 2 columns
                # Sort by x position
                blocks.sort(key=lambda b: b.position['x'])
                valid_rows.append(blocks)
        
        if len(valid_rows) >= self.min_rows:
            # Create table
            table = Table(
                rows=valid_rows[1:],  # Skip header for now
                headers=valid_rows[0] if valid_rows else [],
                bbox=self._calculate_table_bbox(valid_rows)
            )
            self.tables.append(table)
            logger.info(f"Detected table with {len(valid_rows)} rows")
    
    def _calculate_table_bbox(self, rows: List[List[TextBlock]]) -> Tuple[int, int, int, int]:
        """Calculate bounding box for table"""
        all_blocks = [block for row in rows for block in row]
        
        min_x = min(block.position['x'] for block in all_blocks)
        min_y = min(block.position['y'] for block in all_blocks)
        max_x = max(block.position['x'] + block.position['width'] for block in all_blocks)
        max_y = max(block.position['y'] + block.position['height'] for block in all_blocks)
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
    
    def find_text_right_of(self, reference_text: str, 
                          max_distance: int = 200,
                          line_tolerance: int = 20) -> Optional[TextBlock]:
        """
        Find text block to the right of reference text
        
        Args:
            reference_text: Reference text to search for
            max_distance: Maximum horizontal distance
            line_tolerance: Y-axis tolerance for same line
        
        Returns:
            TextBlock if found, None otherwise
        """
        # Find reference block
        reference_block = None
        for block in self.text_blocks:
            if reference_text.lower() in block.text.lower():
                reference_block = block
                break
        
        if not reference_block:
            return None
        
        # Find blocks to the right on the same line
        candidates = []
        ref_y = reference_block.position['y']
        ref_x = reference_block.position['x'] + reference_block.position['width']
        
        for block in self.text_blocks:
            if block == reference_block:
                continue
            
            y_diff = abs(block.position['y'] - ref_y)
            x_diff = block.position['x'] - ref_x
            
            # Must be on same line (within tolerance) and to the right
            if (y_diff <= line_tolerance and 
                0 < x_diff <= max_distance):
                candidates.append((x_diff, block))
        
        if candidates:
            # Return closest candidate
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        return None
    
    def find_text_below(self, reference_text: str,
                       max_distance: int = 100,
                       column_tolerance: int = 50) -> Optional[TextBlock]:
        """
        Find text block below reference text
        
        Args:
            reference_text: Reference text to search for
            max_distance: Maximum vertical distance
            column_tolerance: X-axis tolerance for same column
        
        Returns:
            TextBlock if found, None otherwise
        """
        # Find reference block
        reference_block = None
        for block in self.text_blocks:
            if reference_text.lower() in block.text.lower():
                reference_block = block
                break
        
        if not reference_block:
            return None
        
        # Find blocks below in the same column
        candidates = []
        ref_x = reference_block.position['x']
        ref_y = reference_block.position['y'] + reference_block.position['height']
        
        for block in self.text_blocks:
            if block == reference_block:
                continue
            
            x_diff = abs(block.position['x'] - ref_x)
            y_diff = block.position['y'] - ref_y
            
            # Must be in same column (within tolerance) and below
            if (x_diff <= column_tolerance and 
                0 < y_diff <= max_distance):
                candidates.append((y_diff, block))
        
        if candidates:
            # Return closest candidate
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        return None
    
    def find_text_at_position(self, x: int, y: int, radius: int = 50) -> Optional[TextBlock]:
        """
        Find text block near specified position
        
        Args:
            x: X coordinate
            y: Y coordinate
            radius: Search radius
        
        Returns:
            TextBlock if found, None otherwise
        """
        closest_block = None
        min_distance = float('inf')
        
        for block in self.text_blocks:
            # Calculate distance from block center to target position
            distance = np.sqrt(
                (block.center[0] - x) ** 2 + (block.center[1] - y) ** 2
            )
            
            if distance <= radius and distance < min_distance:
                min_distance = distance
                closest_block = block
        
        return closest_block
    
    def get_lines(self) -> List[Line]:
        """Get all detected lines"""
        return self.lines
    
    def get_columns(self) -> List[Column]:
        """Get all detected columns"""
        return self.columns
    
    def get_tables(self) -> List[Table]:
        """Get all detected tables"""
        return self.tables
    
    def visualize(self, image_path: Optional[str] = None, 
                 output_path: Optional[str] = None) -> str:
        """
        Create visualization of spatial analysis
        
        Args:
            image_path: Path to original image (optional)
            output_path: Output path for visualization (optional)
        
        Returns:
            Path to saved visualization
        """
        if not self.viz_enabled:
            return ""
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        
        # Load original image if provided
        if image_path and os.path.exists(image_path):
            img = cv2.imread(image_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            ax.imshow(img)
        
        # Draw text blocks
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        
        for i, block in enumerate(self.text_blocks):
            x, y, w, h = block.position['x'], block.position['y'], block.position['width'], block.position['height']
            
            # Draw bounding box
            rect = Rectangle((x, y), w, h, linewidth=2, 
                           edgecolor=colors[i % len(colors)], 
                           facecolor='none', alpha=0.7)
            ax.add_patch(rect)
            
            # Add text label
            ax.text(x, y-5, f"{block.text[:20]}", 
                   fontsize=8, color=colors[i % len(colors)], 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
        
        # Draw lines
        for line in self.lines:
            if len(line.blocks) > 1:
                # Draw line connecting blocks
                x_coords = [b.center[0] for b in line.blocks]
                y_coords = [b.center[1] for b in line.blocks]
                ax.plot(x_coords, y_coords, 'r--', alpha=0.5, linewidth=1)
        
        # Draw tables
        for table in self.tables:
            x, y, w, h = table.bbox
            rect = Rectangle((x, y), w, h, linewidth=3, 
                           edgecolor='yellow', facecolor='none', alpha=0.8)
            ax.add_patch(rect)
            ax.text(x, y-10, "TABLE", fontsize=12, color='yellow', weight='bold')
        
        ax.set_title('Spatial OCR Analysis', fontsize=14, weight='bold')
        ax.axis('off')
        
        # Save visualization
        if not output_path:
            output_path = os.path.join(self.output_dir, 'spatial_analysis.png')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Spatial analysis visualization saved to: {output_path}")
        return output_path
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        stats = {
            'total_blocks': len(self.text_blocks),
            'total_lines': len(self.lines),
            'total_columns': len(self.columns),
            'total_tables': len(self.tables),
            'avg_confidence': sum(b.confidence for b in self.text_blocks) / len(self.text_blocks) if self.text_blocks else 0,
            'text_length_distribution': {
                'short': len([b for b in self.text_blocks if len(b.text) < 10]),
                'medium': len([b for b in self.text_blocks if 10 <= len(b.text) < 50]),
                'long': len([b for b in self.text_blocks if len(b.text) >= 50])
            }
        }
        return stats


# Example usage and testing
if __name__ == "__main__":
    import json
    import os
    
    # Load config
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Sample OCR results for testing
    sample_ocr_results = [
        {
            "text": "Invoice No:",
            "confidence": 0.9,
            "bbox": [[50, 120], [200, 120], [200, 140], [50, 140]],
            "position": {"x": 50, "y": 120, "width": 150, "height": 20}
        },
        {
            "text": "INV-001",
            "confidence": 0.92,
            "bbox": [[210, 120], [400, 120], [400, 140], [210, 140]],
            "position": {"x": 210, "y": 120, "width": 190, "height": 20}
        },
        {
            "text": "Date:",
            "confidence": 0.88,
            "bbox": [[50, 160], [120, 160], [120, 180], [50, 180]],
            "position": {"x": 50, "y": 160, "width": 70, "height": 20}
        },
        {
            "text": "2024-01-15",
            "confidence": 0.95,
            "bbox": [[130, 160], [280, 160], [280, 180], [130, 180]],
            "position": {"x": 130, "y": 160, "width": 150, "height": 20}
        }
    ]
    
    # Initialize analyzer
    analyzer = SpatialOCRAnalyzer(config)
    analyzer.load_ocr_results(sample_ocr_results)
    
    # Test spatial functions
    print("Testing spatial analysis...")
    
    # Find text to the right
    invoice_no = analyzer.find_text_right_of("Invoice No:")
    if invoice_no:
        print(f"Found invoice number: {invoice_no.text}")
    
    # Find text below
    date_value = analyzer.find_text_below("Date:")
    if date_value:
        print(f"Found date: {date_value.text}")
    
    # Get statistics
    stats = analyzer.get_statistics()
    print(f"Analysis statistics: {stats}")
    
    # Test visualization (if matplotlib is available)
    try:
        viz_path = analyzer.visualize()
        print(f"Visualization saved to: {viz_path}")
    except Exception as e:
        print(f"Visualization failed: {e}")

