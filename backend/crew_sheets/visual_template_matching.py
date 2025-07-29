"""
Visual Template Matching System
Provides better template suggestions based on image similarity and structure analysis
"""
import cv2
import numpy as np
import logging
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageOps
from django.core.files.storage import default_storage
import tempfile
import os
from .models import SheetTemplate, CrewSheet
from .image_processor import ImagePreprocessor

logger = logging.getLogger(__name__)


class VisualTemplateMatchingService:
    """Advanced template matching using computer vision techniques."""
    
    # Feature detection parameters
    SIFT_FEATURES = 500
    MATCH_THRESHOLD = 0.7
    MIN_MATCH_COUNT = 10
    
    @staticmethod
    def find_matching_templates(
        user,
        sheet_image_path: str,
        limit: int = 5,
        include_visual_analysis: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find matching templates using visual similarity and structure analysis.
        
        Args:
            user: User object
            sheet_image_path: Path to the crew sheet image
            limit: Maximum number of templates to return
            include_visual_analysis: Whether to perform visual analysis
            
        Returns:
            List of template suggestions with similarity scores
        """
        logger.info(f"Finding matching templates for image: {sheet_image_path}")
        
        # Get user's templates
        user_templates = SheetTemplate.objects.filter(
            user=user,
            is_active=True
        ).order_by('-success_rate', '-usage_count')
        
        if not user_templates.exists():
            return []
        
        template_matches = []
        
        try:
            # Analyze input image structure
            input_analysis = VisualTemplateMatchingService._analyze_image_structure(sheet_image_path)
            
            for template in user_templates:
                match_data = {
                    'template_id': str(template.id),
                    'template_name': template.name,
                    'template_type': template.template_type,
                    'description': template.description,
                    'success_rate': template.success_rate,
                    'usage_count': template.usage_count,
                    'company': template.company,
                    'similarity_score': 0.0,
                    'match_reasons': [],
                    'structural_similarity': 0.0,
                    'visual_similarity': 0.0,
                    'header_similarity': 0.0,
                    'confidence': 0.0
                }
                
                # Calculate structural similarity
                if template.header_structure:
                    structural_sim = VisualTemplateMatchingService._calculate_structural_similarity(
                        input_analysis, template
                    )
                    match_data['structural_similarity'] = structural_sim
                    if structural_sim > 0.7:
                        match_data['match_reasons'].append(f'High structural similarity: {structural_sim:.1%}')
                
                # Calculate visual similarity if template has image
                if include_visual_analysis and template.template_image:
                    try:
                        visual_sim = VisualTemplateMatchingService._calculate_visual_similarity(
                            sheet_image_path, template.template_image.path
                        )
                        match_data['visual_similarity'] = visual_sim
                        if visual_sim > 0.6:
                            match_data['match_reasons'].append(f'Good visual similarity: {visual_sim:.1%}')
                    except Exception as e:
                        logger.warning(f"Visual similarity calculation failed for template {template.id}: {str(e)}")
                
                # Calculate header field similarity
                if template.expected_fields:
                    header_sim = VisualTemplateMatchingService._calculate_header_similarity(
                        input_analysis, template.expected_fields
                    )
                    match_data['header_similarity'] = header_sim
                    if header_sim > 0.6:
                        match_data['match_reasons'].append(f'Similar header structure: {header_sim:.1%}')
                
                # Calculate overall similarity score
                weights = {
                    'structural': 0.4,
                    'visual': 0.35,
                    'header': 0.25
                }
                
                overall_similarity = (
                    match_data['structural_similarity'] * weights['structural'] +
                    match_data['visual_similarity'] * weights['visual'] +
                    match_data['header_similarity'] * weights['header']
                )
                
                # Apply template performance bonus
                performance_bonus = (template.success_rate - 0.5) * 0.2
                overall_similarity += performance_bonus
                
                match_data['similarity_score'] = min(1.0, max(0.0, overall_similarity))
                match_data['confidence'] = VisualTemplateMatchingService._calculate_match_confidence(match_data)
                
                template_matches.append(match_data)
        
        except Exception as e:
            logger.error(f"Error in template matching: {str(e)}")
            # Fall back to simple ranking by success rate
            for template in user_templates[:limit]:
                template_matches.append({
                    'template_id': str(template.id),
                    'template_name': template.name,
                    'template_type': template.template_type,
                    'description': template.description,
                    'success_rate': template.success_rate,
                    'usage_count': template.usage_count,
                    'company': template.company,
                    'similarity_score': template.success_rate,
                    'match_reasons': ['High success rate'],
                    'confidence': template.success_rate
                })
        
        # Sort by similarity score and limit results
        template_matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        return template_matches[:limit]
    
    @staticmethod
    def _analyze_image_structure(image_path: str) -> Dict[str, Any]:
        """Analyze the structural properties of an image."""
        try:
            logger.debug(f"Analyzing image structure for: {image_path}")
            
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            
            # Detect horizontal and vertical lines (table structure)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width // 10, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 10))
            
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Count line intersections (grid points)
            table_structure = cv2.bitwise_or(horizontal_lines, vertical_lines)
            contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze text regions
            text_regions = VisualTemplateMatchingService._detect_text_regions(gray)
            
            # Calculate image properties
            analysis = {
                'width': width,
                'height': height,
                'aspect_ratio': width / height,
                'estimated_rows': len([c for c in contours if cv2.contourArea(c) > 100]),
                'estimated_columns': VisualTemplateMatchingService._estimate_columns(gray),
                'text_density': len(text_regions) / (width * height) * 1000000,  # Per million pixels
                'has_table_structure': len(contours) > 5,
                'orientation': 'landscape' if width > height else 'portrait',
                'image_hash': VisualTemplateMatchingService._calculate_image_hash(gray)
            }
            
            logger.debug(f"Image analysis complete: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing image structure: {str(e)}")
            return {
                'width': 0,
                'height': 0,
                'aspect_ratio': 1.0,
                'estimated_rows': 0,
                'estimated_columns': 0,
                'text_density': 0.0,
                'has_table_structure': False,
                'orientation': 'unknown',
                'image_hash': ''
            }
    
    @staticmethod
    def _detect_text_regions(gray_image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect text regions in the image."""
        try:
            # Use MSER (Maximally Stable Extremal Regions) for text detection
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray_image)
            
            # Filter regions by size and aspect ratio
            text_regions = []
            for region in regions:
                x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
                aspect_ratio = w / h if h > 0 else 0
                area = w * h
                
                # Filter for text-like regions
                if 50 < area < 5000 and 0.1 < aspect_ratio < 10:
                    text_regions.append((x, y, w, h))
            
            return text_regions
            
        except Exception as e:
            logger.warning(f"Text region detection failed: {str(e)}")
            return []
    
    @staticmethod
    def _estimate_columns(gray_image: np.ndarray) -> int:
        """Estimate number of columns in the image."""
        try:
            height, width = gray_image.shape
            
            # Look for vertical separators
            vertical_projection = np.sum(gray_image, axis=0)
            
            # Find valleys in the projection (column separators)
            threshold = np.mean(vertical_projection) * 0.8
            valleys = []
            
            for i in range(1, len(vertical_projection) - 1):
                if (vertical_projection[i] < threshold and 
                    vertical_projection[i] < vertical_projection[i-1] and 
                    vertical_projection[i] < vertical_projection[i+1]):
                    valleys.append(i)
            
            # Estimated columns = valleys + 1, but cap at reasonable number
            estimated_columns = min(len(valleys) + 1, 20)
            return max(1, estimated_columns)
            
        except Exception as e:
            logger.warning(f"Column estimation failed: {str(e)}")
            return 1
    
    @staticmethod
    def _calculate_image_hash(gray_image: np.ndarray) -> str:
        """Calculate perceptual hash of the image."""
        try:
            # Resize to standard size for consistent hashing
            resized = cv2.resize(gray_image, (32, 32))
            
            # Calculate average
            avg = np.mean(resized)
            
            # Create hash based on pixels above/below average
            hash_bits = (resized > avg).flatten()
            
            # Convert to hex string
            hash_bytes = np.packbits(hash_bits)
            return hashlib.md5(hash_bytes.tobytes()).hexdigest()[:16]
            
        except Exception as e:
            logger.warning(f"Image hashing failed: {str(e)}")
            return ''
    
    @staticmethod
    def _calculate_structural_similarity(
        input_analysis: Dict[str, Any], 
        template: SheetTemplate
    ) -> float:
        """Calculate structural similarity between input and template."""
        try:
            similarity = 0.0
            comparisons = 0
            
            # Compare aspect ratios
            if 'aspect_ratio' in input_analysis:
                # Template aspect ratio would need to be stored - for now estimate
                template_aspect = 1.3  # Typical landscape crew sheet
                aspect_diff = abs(input_analysis['aspect_ratio'] - template_aspect)
                aspect_similarity = max(0, 1 - aspect_diff / 2)  # Normalize
                similarity += aspect_similarity * 0.3
                comparisons += 0.3
            
            # Compare estimated columns
            if template.header_structure and 'estimated_columns' in input_analysis:
                # Estimate template columns from header structure
                template_columns = len(template.header_structure.get('main_headers', [])) or 5
                column_diff = abs(input_analysis['estimated_columns'] - template_columns)
                column_similarity = max(0, 1 - column_diff / max(template_columns, input_analysis['estimated_columns']))
                similarity += column_similarity * 0.4
                comparisons += 0.4
            
            # Compare orientation
            template_orientation = 'landscape'  # Most crew sheets are landscape
            if input_analysis.get('orientation') == template_orientation:
                similarity += 0.3
                comparisons += 0.3
            
            return similarity / comparisons if comparisons > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Structural similarity calculation failed: {str(e)}")
            return 0.0
    
    @staticmethod
    def _calculate_visual_similarity(image1_path: str, image2_path: str) -> float:
        """Calculate visual similarity between two images using SIFT features."""
        try:
            logger.debug(f"Calculating visual similarity between {image1_path} and {image2_path}")
            
            # Load images
            img1 = cv2.imread(image1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                return 0.0
            
            # Resize images to similar size for fair comparison
            target_height = 800
            h1, w1 = img1.shape
            h2, w2 = img2.shape
            
            if h1 > target_height:
                scale = target_height / h1
                img1 = cv2.resize(img1, (int(w1 * scale), target_height))
            
            if h2 > target_height:
                scale = target_height / h2
                img2 = cv2.resize(img2, (int(w2 * scale), target_height))
            
            # Initialize SIFT detector
            sift = cv2.SIFT_create(nfeatures=VisualTemplateMatchingService.SIFT_FEATURES)
            
            # Detect keypoints and descriptors
            kp1, des1 = sift.detectAndCompute(img1, None)
            kp2, des2 = sift.detectAndCompute(img2, None)
            
            if des1 is None or des2 is None or len(des1) < 2 or len(des2) < 2:
                return 0.0
            
            # Match features using FLANN matcher
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)
            flann = cv2.FlannBasedMatcher(index_params, search_params)
            
            matches = flann.knnMatch(des1, des2, k=2)
            
            # Apply Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < VisualTemplateMatchingService.MATCH_THRESHOLD * n.distance:
                        good_matches.append(m)
            
            # Calculate similarity based on good matches
            if len(good_matches) >= VisualTemplateMatchingService.MIN_MATCH_COUNT:
                similarity = min(1.0, len(good_matches) / 100)  # Normalize to 0-1
                logger.debug(f"Visual similarity: {similarity:.3f} ({len(good_matches)} good matches)")
                return similarity
            else:
                logger.debug(f"Insufficient matches: {len(good_matches)}")
                return 0.0
                
        except Exception as e:
            logger.warning(f"Visual similarity calculation failed: {str(e)}")
            return 0.0
    
    @staticmethod
    def _calculate_header_similarity(
        input_analysis: Dict[str, Any], 
        expected_fields: List[str]
    ) -> float:
        """Calculate similarity based on expected header patterns."""
        try:
            if not expected_fields:
                return 0.0
            
            # Analyze header patterns in expected fields
            time_headers = [f for f in expected_fields if any(
                keyword in f.upper() for keyword in ['START', 'BREAK', 'LUNCH', 'END']
            )]
            job_headers = [f for f in expected_fields if any(
                keyword in f.upper() for keyword in ['HRS', 'HOURS', 'PCS', 'PIECE', 'WORK']
            )]
            hierarchical_headers = [f for f in expected_fields if f.count('_') >= 2]
            
            # Score based on header complexity and structure
            complexity_score = 0.0
            
            if time_headers:
                complexity_score += 0.3  # Has time tracking
            
            if job_headers:
                complexity_score += 0.3  # Has job assignments
            
            if hierarchical_headers:
                complexity_score += 0.4  # Has hierarchical structure
            
            # Adjust based on estimated columns
            estimated_cols = input_analysis.get('estimated_columns', 0)
            expected_cols = len(expected_fields)
            
            if expected_cols > 0:
                column_ratio = min(estimated_cols, expected_cols) / max(estimated_cols, expected_cols)
                complexity_score *= column_ratio
            
            return min(1.0, complexity_score)
            
        except Exception as e:
            logger.warning(f"Header similarity calculation failed: {str(e)}")
            return 0.0
    
    @staticmethod
    def _calculate_match_confidence(match_data: Dict[str, Any]) -> float:
        """Calculate overall confidence in the template match."""
        try:
            confidence = match_data['similarity_score']
            
            # Boost confidence for templates with high success rates
            if match_data['success_rate'] > 0.8:
                confidence += 0.1
            
            # Boost confidence for frequently used templates
            if match_data['usage_count'] > 10:
                confidence += 0.05
            
            # Boost confidence if multiple similarity metrics agree
            similarities = [
                match_data['structural_similarity'],
                match_data['visual_similarity'],
                match_data['header_similarity']
            ]
            
            # Count how many similarities are above threshold
            high_similarities = sum(1 for sim in similarities if sim > 0.6)
            if high_similarities >= 2:
                confidence += 0.1
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {str(e)}")
            return match_data.get('similarity_score', 0.0)


class TemplateCreationAssistant:
    """Assistant for creating templates from successful extractions."""
    
    @staticmethod
    def suggest_template_creation(
        crew_sheet: CrewSheet,
        extraction_confidence: float = 0.8
    ) -> Optional[Dict[str, Any]]:
        """Suggest creating a template based on successful extraction."""
        
        if extraction_confidence < 0.8:
            return None
        
        # Check if user already has similar templates
        user_templates = SheetTemplate.objects.filter(
            user=crew_sheet.user,
            is_active=True
        )
        
        if not crew_sheet.extracted_data:
            return None
        
        extracted_headers = crew_sheet.extracted_data.get('table_headers', [])
        if not extracted_headers:
            return None
        
        # Check for similar existing templates
        for template in user_templates:
            if template.expected_fields:
                similarity = len(set(extracted_headers) & set(template.expected_fields)) / \
                           max(len(extracted_headers), len(template.expected_fields))
                if similarity > 0.8:
                    return None  # Too similar to existing template
        
        # Suggest template creation
        return {
            'should_create_template': True,
            'suggested_name': f"Template_{crew_sheet.date_uploaded.strftime('%Y%m%d')}",
            'suggested_type': TemplateCreationAssistant._suggest_template_type(extracted_headers),
            'confidence': extraction_confidence,
            'extracted_headers': extracted_headers,
            'unique_patterns': TemplateCreationAssistant._identify_unique_patterns(extracted_headers)
        }
    
    @staticmethod
    def _suggest_template_type(headers: List[str]) -> str:
        """Suggest template type based on headers."""
        header_text = ' '.join(headers).upper()
        
        if 'PIECE' in header_text or 'PCS' in header_text:
            return 'piece_work'
        elif 'TIME' in header_text or 'START' in header_text or 'BREAK' in header_text:
            return 'time_tracking'
        elif 'JOB' in header_text and 'HRS' in header_text:
            return 'job_tracking'
        else:
            return 'general'
    
    @staticmethod
    def _identify_unique_patterns(headers: List[str]) -> List[str]:
        """Identify unique patterns in the headers."""
        patterns = []
        
        # Check for hierarchical patterns
        hierarchical = [h for h in headers if h.count('_') >= 2]
        if hierarchical:
            patterns.append(f"Hierarchical headers: {len(hierarchical)} found")
        
        # Check for time patterns
        time_headers = [h for h in headers if any(
            keyword in h.upper() for keyword in ['START', 'BREAK', 'LUNCH', 'END']
        )]
        if time_headers:
            patterns.append(f"Time tracking: {len(time_headers)} columns")
        
        # Check for job patterns
        job_headers = [h for h in headers if any(
            keyword in h.upper() for keyword in ['HRS', 'HOURS', 'PCS', 'PIECE', 'WORK']
        )]
        if job_headers:
            patterns.append(f"Job assignments: {len(job_headers)} columns")
        
        return patterns