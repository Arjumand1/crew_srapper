"""
Advanced Image Preprocessing for Better OCR Results
Optimizes images before sending to OpenAI Vision API for improved accuracy.
"""
import os
import cv2
import numpy as np
import logging
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Advanced image preprocessing for optimal OCR results."""

    # Optimal dimensions for GPT-4V
    MAX_DIMENSION = 1024
    MIN_DIMENSION = 512

    @staticmethod
    def optimize_for_ocr(image_path: str, aggressive: bool = False) -> str:
        """
        Preprocess image for better OCR results.

        Args:
            image_path: Path to the original image
            aggressive: Whether to apply more aggressive preprocessing

        Returns:
            Path to the optimized image
        """
        try:
            logger.info(f"Starting image preprocessing for: {image_path}")

            # Load image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Store original info
                original_size = img.size
                logger.info(f"Original image size: {original_size}")

                # Stage 1: Resize for optimal processing
                img = ImagePreprocessor._optimal_resize(img)

                # Stage 2: Enhance for text recognition
                img = ImagePreprocessor._enhance_for_text(img, aggressive)

                # Stage 3: Noise reduction
                img = ImagePreprocessor._reduce_noise(img)

                # Stage 4: Final optimization
                img = ImagePreprocessor._final_optimization(img)

                # Save optimized image
                processed_path = ImagePreprocessor._get_processed_path(
                    image_path)
                img.save(processed_path, 'JPEG', quality=95, optimize=True)

                logger.info(
                    f"Image preprocessing completed. Saved to: {processed_path}")
                return processed_path

        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            # Return original path if preprocessing fails
            return image_path

    @staticmethod
    def _optimal_resize(img: Image.Image) -> Image.Image:
        """Resize image to optimal dimensions for GPT-4V processing."""
        width, height = img.size

        # If image is too small, upscale it
        if max(width, height) < ImagePreprocessor.MIN_DIMENSION:
            scale_factor = ImagePreprocessor.MIN_DIMENSION / max(width, height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = img.resize((new_width, new_height), Image.Lanczos)
            logger.info(f"Upscaled image to: {new_width}x{new_height}")

        # If image is too large, downscale it
        elif max(width, height) > ImagePreprocessor.MAX_DIMENSION:
            img.thumbnail((ImagePreprocessor.MAX_DIMENSION,
                          ImagePreprocessor.MAX_DIMENSION), Image.Lanczos)
            logger.info(f"Downscaled image to: {img.size}")

        return img

    @staticmethod
    def _enhance_for_text(img: Image.Image, aggressive: bool = False) -> Image.Image:
        """Enhance image specifically for better text recognition."""

        # Convert to grayscale for better text processing
        if img.mode != 'L':
            img = img.convert('L')

        # Enhance contrast
        contrast_factor = 2.5 if aggressive else 2.0
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)

        # Enhance sharpness
        sharpness_factor = 2.0 if aggressive else 1.5
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpness_factor)

        # Auto-level to improve dynamic range
        img = ImageOps.autocontrast(img, cutoff=1)

        # Convert back to RGB for OpenAI API
        img = img.convert('RGB')

        return img

    @staticmethod
    def _reduce_noise(img: Image.Image) -> Image.Image:
        """Apply noise reduction filters."""

        # Convert to OpenCV format for advanced filtering
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Apply bilateral filter to reduce noise while preserving edges
        cv_img = cv2.bilateralFilter(cv_img, 9, 75, 75)

        # Apply morphological operations to clean up text
        kernel = np.ones((2, 2), np.uint8)
        cv_img = cv2.morphologyEx(cv_img, cv2.MORPH_CLOSE, kernel)

        # Convert back to PIL
        img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

        return img

    @staticmethod
    def _final_optimization(img: Image.Image) -> Image.Image:
        """Apply final optimizations for OCR."""

        # Slight gaussian blur to smooth out pixelation
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

        # Final contrast adjustment
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)

        return img

    @staticmethod
    def _get_processed_path(original_path: str) -> str:
        """Generate path for processed image."""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        directory = os.path.dirname(original_path)
        return os.path.join(directory, f"{base_name}_processed.jpg")

    @staticmethod
    def assess_image_quality(image_path: str) -> dict:
        """
        Assess image quality metrics for preprocessing decisions.

        Returns:
            Dictionary with quality metrics
        """
        try:
            with Image.open(image_path) as img:
                # Convert to grayscale for analysis
                gray_img = img.convert('L')
                img_array = np.array(gray_img)

                # Calculate quality metrics
                metrics = {
                    'resolution': img.size,
                    'aspect_ratio': img.size[0] / img.size[1],
                    'brightness': np.mean(img_array),
                    'contrast': np.std(img_array),
                    'sharpness': ImagePreprocessor._calculate_sharpness(img_array),
                    'noise_level': ImagePreprocessor._estimate_noise(img_array)
                }

                # Overall quality score (0-1)
                metrics['overall_quality'] = ImagePreprocessor._calculate_overall_quality(
                    metrics)

                return metrics

        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}")
            return {
                'resolution': (0, 0),
                'aspect_ratio': 1.0,
                'brightness': 128,
                'contrast': 50,
                'sharpness': 0.5,
                'noise_level': 0.5,
                'overall_quality': 0.5
            }

    @staticmethod
    def _calculate_sharpness(img_array: np.ndarray) -> float:
        """Calculate sharpness using Laplacian variance."""
        laplacian = cv2.Laplacian(img_array, cv2.CV_64F)
        return np.var(laplacian) / 10000  # Normalize

    @staticmethod
    def _estimate_noise(img_array: np.ndarray) -> float:
        """Estimate noise level in image."""
        # Use standard deviation of high-frequency components
        kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
        filtered = cv2.filter2D(img_array, -1, kernel)
        noise_level = np.std(filtered) / 255.0  # Normalize to 0-1
        return min(noise_level, 1.0)

    @staticmethod
    def _calculate_overall_quality(metrics: dict) -> float:
        """Calculate overall quality score from individual metrics."""

        # Normalize metrics to 0-1 scale
        # Prefer medium brightness
        brightness_score = 1.0 - abs(metrics['brightness'] - 128) / 128
        # Higher contrast is better
        contrast_score = min(metrics['contrast'] / 100, 1.0)
        # Higher sharpness is better
        sharpness_score = min(metrics['sharpness'], 1.0)
        # Lower noise is better
        noise_score = 1.0 - min(metrics['noise_level'], 1.0)

        # Resolution score
        pixel_count = metrics['resolution'][0] * metrics['resolution'][1]
        # Prefer higher resolution up to 1MP
        resolution_score = min(pixel_count / (1024 * 1024), 1.0)

        # Weighted average
        weights = {
            'brightness': 0.15,
            'contrast': 0.25,
            'sharpness': 0.25,
            'noise': 0.20,
            'resolution': 0.15
        }

        overall_score = (
            brightness_score * weights['brightness'] +
            contrast_score * weights['contrast'] +
            sharpness_score * weights['sharpness'] +
            noise_score * weights['noise'] +
            resolution_score * weights['resolution']
        )

        return round(overall_score, 3)


class AdaptivePreprocessor:
    """Adaptive preprocessing based on image characteristics."""

    @staticmethod
    def preprocess_adaptive(image_path: str) -> str:
        """
        Apply adaptive preprocessing based on image quality assessment.

        Args:
            image_path: Path to the original image

        Returns:
            Path to the optimized image
        """
        # Assess image quality first
        quality_metrics = ImagePreprocessor.assess_image_quality(image_path)

        # Determine preprocessing strategy based on quality
        if quality_metrics['overall_quality'] < 0.4:
            # Poor quality image - aggressive preprocessing
            logger.info(
                "Applying aggressive preprocessing for poor quality image")
            return ImagePreprocessor.optimize_for_ocr(image_path, aggressive=True)

        elif quality_metrics['contrast'] < 30:
            # Low contrast image - focus on contrast enhancement
            logger.info("Applying contrast-focused preprocessing")
            return AdaptivePreprocessor._enhance_contrast_focused(image_path)

        elif quality_metrics['sharpness'] < 0.3:
            # Blurry image - focus on sharpening
            logger.info("Applying sharpness-focused preprocessing")
            return AdaptivePreprocessor._enhance_sharpness_focused(image_path)

        else:
            # Good quality image - standard preprocessing
            logger.info(
                "Applying standard preprocessing for good quality image")
            return ImagePreprocessor.optimize_for_ocr(image_path, aggressive=False)

    @staticmethod
    def _enhance_contrast_focused(image_path: str) -> str:
        """Preprocessing focused on contrast enhancement."""
        try:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Resize optimally
                img = ImagePreprocessor._optimal_resize(img)

                # Convert to LAB color space for better contrast control
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2LAB)

                # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                cv_img[:, :, 0] = clahe.apply(cv_img[:, :, 0])

                # Convert back to RGB
                img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_LAB2RGB))

                # Additional sharpening
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.5)

                # Save processed image
                processed_path = ImagePreprocessor._get_processed_path(
                    image_path)
                img.save(processed_path, 'JPEG', quality=95, optimize=True)

                return processed_path

        except Exception as e:
            logger.error(f"Contrast-focused preprocessing failed: {str(e)}")
            return image_path

    @staticmethod
    def _enhance_sharpness_focused(image_path: str) -> str:
        """Preprocessing focused on sharpness enhancement."""
        try:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Resize optimally
                img = ImagePreprocessor._optimal_resize(img)

                # Convert to OpenCV for advanced sharpening
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                # Apply unsharp mask filter
                gaussian = cv2.GaussianBlur(cv_img, (0, 0), 2.0)
                cv_img = cv2.addWeighted(cv_img, 2.0, gaussian, -1.0, 0)

                # Apply sharpening kernel
                kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
                cv_img = cv2.filter2D(cv_img, -1, kernel)

                # Convert back to PIL
                img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

                # Final contrast adjustment
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)

                # Save processed image
                processed_path = ImagePreprocessor._get_processed_path(
                    image_path)
                img.save(processed_path, 'JPEG', quality=95, optimize=True)

                return processed_path

        except Exception as e:
            logger.error(f"Sharpness-focused preprocessing failed: {str(e)}")
            return image_path
