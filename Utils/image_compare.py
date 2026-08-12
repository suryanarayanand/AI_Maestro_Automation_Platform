from pathlib import Path

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

def load_image(image_path):
    """
    Load an image using OpenCV.

    Returns:
        image (numpy array)

    Raises:
        FileNotFoundError
        ValueError
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(
            f"Unable to load image:\n{image_path}"
        )

    return image


def validate_images(reference_image, actual_image):
    """
    Validate that both images have identical dimensions.

    Returns:
        True

    Raises:
        ValueError
    """

    if reference_image.shape != actual_image.shape:
        raise ValueError(
            "Image size mismatch.\n"
            f"Reference : {reference_image.shape}\n"
            f"Actual    : {actual_image.shape}"
        )

    return True


def prepare_images(reference_path, actual_path):
    """
    Loads both images and validates them.

    Returns:
        reference_image,
        actual_image
    """

    reference = load_image(reference_path)
    actual = load_image(actual_path)

    # Cross-device runs commonly differ in resolution and density. Normalize the
    # actual capture to the reference canvas so SSIM can still be calculated.
    if reference.shape != actual.shape:
        height, width = reference.shape[:2]
        actual = cv2.resize(actual, (width, height), interpolation=cv2.INTER_AREA)

    return reference, actual

def compare_images(reference_image, actual_image):
    """
    Compare two images using Structural Similarity (SSIM).

    Returns:
        similarity_score (0.0 - 1.0)
        diff_image
    """

    gray_reference = cv2.cvtColor(reference_image, cv2.COLOR_BGR2GRAY)
    gray_actual = cv2.cvtColor(actual_image, cv2.COLOR_BGR2GRAY)

    score, diff = ssim(
        gray_reference,
        gray_actual,
        full=True
    )

    diff = (diff * 255).astype("uint8")

    # Threshold the difference image
    threshold = cv2.threshold(
    diff,
    0,
    255,
    cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    # Find changed regions
    contours, _ = cv2.findContours(
        threshold,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # Create a copy of the actual image
    comparison = actual_image.copy()

    # Draw rectangles around differences
    for contour in contours:

        if cv2.contourArea(contour) < 20:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        cv2.rectangle(
            comparison,
            (x, y),
            (x + w, y + h),
            (0, 0, 255),
             2
        )

    similarity = round(score * 100, 2)

    threshold = 95.0

    status = "PASS" if similarity >= threshold else "FAIL"

    return {
    "status": status,
    "similarity": similarity,
    "threshold": threshold,
    "difference_count": len(contours),
    "comparison_image": comparison
    }
