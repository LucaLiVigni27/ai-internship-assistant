from pathlib import Path
from pypdf import PdfReader

def extract_text_from_file(file_path: str, filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_text(file_path)
    elif suffix in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Supported types are: .pdf, .txt, .md")

def extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages_text = [page.extract_text() for page in reader.pages]
    return "\n\n".join(pages_text).strip()