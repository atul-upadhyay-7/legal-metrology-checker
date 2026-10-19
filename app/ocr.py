import io
import pytesseract
from PIL import Image, ImageOps


def extract_text(data: bytes) -> str:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("L")
    if img.width < 1200:
        scale = 1200 / img.width
        img = img.resize((1200, int(img.height * scale)))
    return pytesseract.image_to_string(img, config="--psm 6")
