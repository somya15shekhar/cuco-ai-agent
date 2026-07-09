import pdfplumber


def extract_pdf_text(pdf_path: str) -> str:
    """Extracts all visible text from a PDF file page by page.

    Args:
        pdf_path (str): The absolute or relative path to the PDF file.

    Returns:
        str: Raw text extracted from the PDF file.
    """
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text
