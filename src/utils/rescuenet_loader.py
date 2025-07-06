# src/utils/rescuenet_loader.py
import os
import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging


class RescueNetLoader:
    """
    Loader for RescueNet dataset - handles image loading and metadata
    Works with Hurricane Michael UAV imagery for disaster assessment
    """

    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.images_dir = self.dataset_path / "images"
        self.annotations_dir = self.dataset_path / "annotations"
        self.metadata_file = self.dataset_path / "metadata.json"

        self.logger = logging.getLogger(__name__)

        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}

        # Cache for image list
        self._image_cache = None

        # Initialize dataset
        self._validate_dataset()

    def _validate_dataset(self):
        """Validate dataset structure and create if missing"""
        try:
            # Create directories if they don't exist
            self.dataset_path.mkdir(parents=True, exist_ok=True)
            self.images_dir.mkdir(exist_ok=True)

            # Check if we have images
            image_count = len(self.get_all_images())

            if image_count == 0:
                self.logger.warning(f"No images found in {self.images_dir}")
                self.logger.info("You can download RescueNet dataset from:")
                self.logger.info(
                    "https://github.com/BinaLab/RescueNet-A-High-Resolution-Post-Disaster-UAV-Dataset-for-Semantic-Segmentation")

                # Create sample structure for development
                self._create_sample_structure()
            else:
                self.logger.info(
                    f"Found {image_count} images in RescueNet dataset")

        except Exception as e:
            self.logger.error(f"Error validating dataset: {e}")

    def _create_sample_structure(self):
        """Create sample dataset structure for development/testing"""
        sample_dir = self.images_dir / "samples"
        sample_dir.mkdir(exist_ok=True)

        # Create placeholder metadata
        sample_metadata = {
            "dataset": "RescueNet-Sample",
            "description": "Sample structure for Hurricane Michael disaster assessment",
            "hurricane": "Michael",
            "date": "2018-10-10",
            "location": "Mexico Beach, FL",
            "total_images": 0,
            "damage_categories": [
                "no-damage", "minor-damage", "major-damage", "total-destruction"
            ],
            "note": "Download full dataset from GitHub repository"
        }

        with open(self.metadata_file, 'w') as f:
            json.dump(sample_metadata, f, indent=2)

        # Create a README for users
        readme_content = """
# RescueNet Dataset Setup

This directory structure is prepared for the RescueNet dataset.

## Download Instructions:

1. Visit: https://github.com/BinaLab/RescueNet-A-High-Resolution-Post-Disaster-UAV-Dataset-for-Semantic-Segmentation
2. Download the dataset images
3. Extract to: data/rescuenet/images/
4. The system will automatically detect and process the images

## Dataset Information:
- 4,494 post-disaster images from Hurricane Michael
- High-resolution UAV imagery
- Pixel-level damage annotations
- Categories: buildings, roads, debris, water, vehicles, trees, pools

## Alternative: Use Sample Images
Place any disaster-related images in data/rescuenet/images/ for testing.
        """

        readme_path = self.dataset_path / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)

        self.logger.info(f"Created sample structure at {self.dataset_path}")
        self.logger.info(f"See {readme_path} for download instructions")

    def get_all_images(self) -> List[str]:
        """Get list of all image files in the dataset"""
        if self._image_cache is None:
            self._image_cache = []

            if self.images_dir.exists():
                for file_path in self.images_dir.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                        self._image_cache.append(str(file_path))

            self._image_cache.sort()  # Consistent ordering

        return self._image_cache

    def get_image_batch(self, batch_size: int = 10, random_selection: bool = True) -> List[str]:
        """
        Get a batch of images for processing
        
        Args:
            batch_size: Number of images to return
            random_selection: If True, randomly select images; if False, take first N
        
        Returns:
            List of image file paths
        """
        all_images = self.get_all_images()

        if not all_images:
            self.logger.warning("No images available for batch processing")
            return []

        # Limit batch size to available images
        actual_batch_size = min(batch_size, len(all_images))

        if random_selection:
            return random.sample(all_images, actual_batch_size)
        else:
            return all_images[:actual_batch_size]

    def get_images_by_pattern(self, pattern: str) -> List[str]:
        """
        Get images matching a specific pattern
        
        Args:
            pattern: Glob pattern to match (e.g., "*damage*", "mexico_beach*")
        
        Returns:
            List of matching image paths
        """
        all_images = self.get_all_images()
        matching_images = []

        for image_path in all_images:
            image_name = Path(image_path).name.lower()
            if pattern.lower() in image_name:
                matching_images.append(image_path)

        return matching_images

    def get_dataset_info(self) -> Dict:
        """Get dataset metadata and statistics"""
        all_images = self.get_all_images()

        # Load metadata if available
        metadata = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load metadata: {e}")

        # Calculate basic statistics
        stats = {
            "total_images": len(all_images),
            "dataset_path": str(self.dataset_path),
            "images_directory": str(self.images_dir),
            "supported_formats": list(self.supported_formats),
            # First 5 for preview
            "sample_images": [Path(img).name for img in all_images[:5]],
            "metadata": metadata
        }

        return stats

    def create_test_batch(self, test_size: int = 5) -> List[str]:
        """
        Create a small test batch for development/demo purposes
        
        Args:
            test_size: Number of images for testing
            
        Returns:
            List of test image paths
        """
        return self.get_image_batch(batch_size=test_size, random_selection=True)

    def validate_image_path(self, image_path: str) -> bool:
        """
        Validate that an image path exists and is a supported format
        
        Args:
            image_path: Path to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            path = Path(image_path)
            return (path.exists() and
                    path.is_file() and
                    path.suffix.lower() in self.supported_formats)
        except Exception:
            return False

    def get_image_info(self, image_path: str) -> Optional[Dict]:
        """
        Get information about a specific image
        
        Args:
            image_path: Path to the image
            
        Returns:
            Dictionary with image information or None if not found
        """
        if not self.validate_image_path(image_path):
            return None

        path = Path(image_path)

        try:
            stat = path.stat()

            info = {
                "filename": path.name,
                "full_path": str(path.absolute()),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "format": path.suffix.lower(),
                "last_modified": stat.st_mtime,
                "relative_to_dataset": str(path.relative_to(self.dataset_path))
            }

            return info

        except Exception as e:
            self.logger.error(
                f"Error getting image info for {image_path}: {e}")
            return None

    def search_images(self, search_term: str) -> List[str]:
        """
        Search for images by filename
        
        Args:
            search_term: Term to search for in filenames
            
        Returns:
            List of matching image paths
        """
        all_images = self.get_all_images()
        search_term_lower = search_term.lower()

        matching_images = []
        for image_path in all_images:
            filename = Path(image_path).name.lower()
            if search_term_lower in filename:
                matching_images.append(image_path)

        return matching_images

    def clear_cache(self):
        """Clear the image cache to force refresh"""
        self._image_cache = None
        self.logger.info("Image cache cleared")

    def get_random_image(self) -> Optional[str]:
        """Get a single random image from the dataset"""
        all_images = self.get_all_images()
        if all_images:
            return random.choice(all_images)
        return None
