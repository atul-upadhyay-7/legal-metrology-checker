"""Generate sample label images into samples/. Run: python scripts/make_samples.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "samples"
OUT.mkdir(exist_ok=True)

LABELS = {
    "01_compliant": """SUNRISE FOODS Masala Oats
Net Quantity: 500 g
MRP: Rs 120.00 (Inclusive of all taxes)
Mfg Date: 08/2026
Manufactured by: Sunrise Foods Pvt Ltd,
Plot 12, Sector 5, Industrial Area, Pune 411019
Consumer Care: 1800 123 4567
care@sunrisefoods.example
Country of Origin: India""",
    "02_missing_mrp_tax": """PURE GLOW Face Wash
Net Qty: 100 ml
MRP: Rs 249.00
Mfg: 07/2026
Marketed by: Pure Glow Cosmetics,
45 MG Road, Bengaluru 560001
Customer Care: 080 4567 8901
Made in India""",
    "03_missing_origin_care": """DAILY FRESH Biscuits
Net Wt: 250 g
M.R.P. Rs. 40 incl. of all taxes
Pkd: Sep 2026
Packed by: Daily Fresh Bakers, Nagar Road, Delhi 110001""",
    "04_expiry_only_review": """GREEN LEAF Tea
Net Content: 1 kg
MRP Rs 450 inclusive of all taxes
Best Before: 12 months from packing
Manufactured by: Green Leaf Estates, Tea Road, Darjeeling 734101
Consumer Complaints: 1800 222 3333
Product of India""",
    "05_empty_label": """FANCY SNACKS
Crunchy and tasty
Buy now""",
}

try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
except OSError:
    FONT = ImageFont.load_default()

for name, text in LABELS.items():
    lines = text.split("\n")
    img = Image.new("RGB", (1100, 60 + 48 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((30, 30 + 48 * i), line, fill="black", font=FONT)
    img.save(OUT / f"{name}.png")
    (OUT / f"{name}.txt").write_text(text + "\n")
print("done")
