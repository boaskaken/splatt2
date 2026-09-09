"""Generate the source-controlled target icon. Run from any working directory."""
from pathlib import Path
from PIL import Image, ImageDraw


def generate():
    assets = Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(exist_ok=True)
    size = 1024
    image = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(image)
    rings = [(480, "#222831"), (442, "#fbe2a9"), (334, "#222831"),
             (304, "#fbe2a9"), (230, "#222831"), (160, "#fbe2a9"),
             (132, "#222831"), (60, "#f05a28")]
    for radius, colour in rings:
        draw.ellipse((512-radius, 512-radius, 512+radius, 512+radius), fill=colour)
    image.resize((256, 256), Image.Resampling.LANCZOS).save(assets / "splatt2.png")
    image.save(assets / "splatt2.ico", bitmap_format="bmp", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    image.save(assets / "splatt2.icns")
    circles = "\n".join(f'<circle cx="512" cy="512" r="{r}" fill="{c}"/>' for r, c in rings)
    (assets / "splatt2.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">\n' + circles + '\n</svg>\n',
        encoding="utf-8")


if __name__ == "__main__":
    generate()
