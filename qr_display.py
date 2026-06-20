"""Terminal QR code display."""

import qrcode
from PIL import Image
import os
import sys


def _is_unicode_supported() -> bool:
    """Check if terminal supports Unicode block characters."""
    if "TERM" not in os.environ:
        return False
    term = os.environ.get("TERM", "")
    if term in ("dumb", "") or term.endswith("-256color") == False and len(term) < 5:
        return False
    return True


def _img_to_unicode_block(img: Image.Image) -> list[str]:
    """Convert QR image to Unicode block chars (▀▄█⎵).

    Each pair of pixel rows → one output line, giving ~2x taller QR.
    """
    img = img.convert("L")
    w, h = img.size
    pixels = list(img.getdata())

    lines: list[str] = []
    for row in range(0, h - 1, 2):
        chars: list[str] = []
        for col in range(w):
            top_px = pixels[row * w + col]
            bot_px = pixels[(row + 1) * w + col]
            t_bl = top_px < 128
            b_bl = bot_px < 128
            if t_bl and b_bl:
                chars.append("█")
            elif t_bl:
                chars.append("▀")
            elif b_bl:
                chars.append("▄")
            else:
                chars.append("⎵")
        lines.append("".join(chars))
    return lines


def _img_to_ascii_qr(img: Image.Image, cols: int) -> list[str]:
    """Fallback ASCII QR (no Unicode support)."""
    img_s = img.resize((cols, cols * 2 // 3), Image.NEAREST).convert("L")
    w, h = img_s.size
    pixels = list(img_s.getdata())
    lines: list[str] = []
    for r in range(h):
        chars = []
        for c in range(w):
            if pixels[r * w + c] < 128:
                chars.append("█")
            else:
                chars.append(" ")
        lines.append("".join(chars))
    return lines


def generate_terminal_qr(connection_url: str, token_short: str = "") -> None:
    """Print a scannable QR code in the terminal.

    The QR encodes `connection_url` (e.g. "https://xxx.ngrok.io/?token=yyy")
    so scanning it directly connects from a browser without typing anything.

    Parameters:
        connection_url: Full URL to encode in QR (with token as query param).
        token_short: Short display of the token for reference below the QR.
    """
    supported = _is_unicode_supported()

    try:
        qr = qrcode.QRCode(
            version=1,  # smallest possible QR (21x21 modules)
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,  # compact
            border=1,
        )
        qr.add_data(connection_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
    except Exception as exc:
        print(f"[!] QR generation failed: {exc}", file=sys.stderr)
        return

    if supported:
        lines = _img_to_unicode_block(img)
        max_w = max(len(l) for l in lines)
        pad = 4
        sep_h = "═"
        sep_v = "║"

        print(f"{sep_h * (max_w + pad*2 + 2)}")
        print(f"{sep_v}  Scan to connect from phone:{' '*(max_w + pad - 16)}{sep_v}")
        for line in lines:
            inner = " " * pad + line
            right_pad = max_w - len(line)
            full_line = inner + " " * right_pad
            print(f"{sep_v}{full_line}{sep_v}")
        # Empty row before URL
        print(f"{sep_v}{' '*(max_w + pad*2)}{sep_v}")
        url_label = f"  URL: {connection_url}"
        remaining = max_w + pad - len("URL:") - 1
        print(f"{sep_v}{url_label:<{remaining}}     {sep_v}")
        print(f"{sep_h * (max_w + pad*2 + 2)}")

        if token_short:
            print()
            print("=" * 50)
            print("  Token (also pasted in browser):")
            print(f"  {token_short}")
            print("=" * 50)
    else:
        # ASCII fallback — limit width to terminal-safe ~30 columns
        lines = _img_to_ascii_qr(img, 30)
        max_w = max(len(l) for l in lines)
        pad = 4
        print("+" + "-" * (max_w + pad*2 + 2) + "+")
        print("|" + " "*pad + "Scan from phone:" + " "*(max_w+pad-14) + "|")
        for line in lines:
            inner = " "*pad + line
            right_pad = max_w - len(line)
            full_line = inner + " "*right_pad
            print("|" + full_line + "|")
        print("|" + " "*(max_w+pad*2) + "|")
        print(f"|  URL: {connection_url:<{max_w+pad-6}}  |")
        print("+" + "-" * (max_w + pad*2 + 2) + "+")

        if token_short:
            print()
            print("=" * 50)
            print("  Token (also pasted in browser):")
            print(f"  {token_short}")
            print("=" * 50)


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "http://example.ngrok.io/?token=test123"
    generate_terminal_qr(test_url, "test123")
