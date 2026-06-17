# loader.py
# Extraction de texte depuis PDF et images

import pytesseract
from PIL import Image
from pypdf import PdfReader
import io

import os

# Chemin vers Tesseract sur Windows
# A adapter si vous avez installe dans un autre dossier
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def load_pdf(file_bytes: bytes) -> str:
    """
    Extrait le texte d un fichier PDF.
    Essaie d abord l extraction native (PDF textuel).
    Si le texte est vide, bascule sur l OCR (PDF scanne).

    Parametres :
    ------------
    file_bytes : bytes
        Contenu brut du fichier PDF

    Retour :
    --------
    str
        Texte extrait du PDF
    """
    # Lecture du PDF depuis les bytes
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""

    for page in reader.pages:
        # Extraction native du texte de la page
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    # Si aucun texte extrait, le PDF est probablement scanne
    # On bascule sur l OCR page par page
    if not text.strip():
        text = ocr_pdf(reader)

    return text.strip()


def ocr_pdf(reader: PdfReader) -> str:
    """
    Applique l OCR sur un PDF scanne.
    Convertit chaque page en image puis extrait le texte.

    Parametres :
    ------------
    reader : PdfReader
        Objet PdfReader deja initialise

    Retour :
    --------
    str
        Texte extrait par OCR
    """
    text = ""

    for i, page in enumerate(reader.pages):
        # Recupere les images embedees dans la page
        for image_obj in page.images:
            image = Image.open(io.BytesIO(image_obj.data))
            # OCR en francais et anglais
            page_text = pytesseract.image_to_string(
                image,
                lang="fra+eng"
            )
            text += page_text + "\n"
        print(f"[LOADER] Page {i+1} traitee par OCR")

    return text


def load_image(file_bytes: bytes) -> str:
    """
    Extrait le texte d une image via OCR.
    Supporte : PNG, JPG, JPEG, TIFF, BMP

    Parametres :
    ------------
    file_bytes : bytes
        Contenu brut de l image

    Retour :
    --------
    str
        Texte extrait de l image
    """
    image = Image.open(io.BytesIO(file_bytes))

    # OCR en francais et anglais
    text = pytesseract.image_to_string(
        image,
        lang="fra+eng"
    )

    return text.strip()


def load_file(file_bytes: bytes, filename: str) -> str:
    """
    Fonction principale du loader.
    Detecte le type de fichier et appelle
    la bonne methode d extraction.

    Parametres :
    ------------
    file_bytes : bytes
        Contenu brut du fichier
    filename : str
        Nom du fichier avec extension

    Retour :
    --------
    str
        Texte extrait pret pour le chunker
    """
    extension = filename.lower().split(".")[-1]

    if extension == "pdf":
        print(f"[LOADER] Traitement PDF : {filename}")
        return load_pdf(file_bytes)

    elif extension in ["png", "jpg", "jpeg", "tiff", "bmp"]:
        print(f"[LOADER] Traitement image : {filename}")
        return load_image(file_bytes)

    else:
        # Format non supporte
        raise ValueError(
            f"Format non supporte : {extension}. "
            f"Formats acceptes : pdf, png, jpg, jpeg, tiff, bmp"
     )