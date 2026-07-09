import pytesseract
from PIL import Image

# Only needed if Tesseract isn't in your PATH
# Uncomment and update if required.
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_image_text(image_path: str) -> str:
    """
    Reads an image and extracts all visible text using OCR.
    """

    # Open the image
    image = Image.open(image_path)

    # Run OCR
    text = pytesseract.image_to_string(image)

    return text