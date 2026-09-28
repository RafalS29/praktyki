import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT_OK = ROOT / "pytest_wynik_OK.png"
OUTPUT_FAIL = ROOT / "pytest_wynik_FAIL.png"


def load_font(size=18):
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def save_terminal_png(text, path):
    lines = text.splitlines() or [""]
    font = load_font()
    padding = 24
    line_height = 24
    width = max(1000, min(1800, max(len(line) for line in lines) * 11 + padding * 2))
    height = max(300, len(lines) * line_height + padding * 2)

    image = Image.new("RGB", (width, height), (18, 18, 18))
    draw = ImageDraw.Draw(image)

    y = padding
    for line in lines:
        draw.text((padding, y), line, font=font, fill=(235, 235, 235))
        y += line_height

    image.save(path)


def main():
    env = os.environ.copy()
    env.setdefault(
        "JWT_SECRET",
        "pytest-secret-key-which-is-long-enough-123456"
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "tests/test_security_pytest.py",
    ]

    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    output = (
        f"> {' '.join(command)}\n\n"
        + result.stdout
        + ("\nSTDERR:\n" + result.stderr if result.stderr else "")
    )

    print(output)

    if result.returncode == 0:
        save_terminal_png(output, OUTPUT_OK)
        print(f"\n[OK] Zapisano zrzut wyniku: {OUTPUT_OK.name}")
        return 0

    save_terminal_png(output, OUTPUT_FAIL)
    print(f"\n[BLAD] Testy nie przeszly. Zapisano: {OUTPUT_FAIL.name}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
