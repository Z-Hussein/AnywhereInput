"""Terminal QR code display for quick mobile access."""

import io as _io_mod
from anywhereinput import safe_print, safe_print_stderr


def display_qr(url: str, token: str) -> None:
    """Display a QR code in the terminal for the given URL.

    The QR encodes the full client link with the token baked in,
    so scanning auto-fills both server and token fields.
    """
    full_link = f"{url}/?token={token}"
    try:
        qr = __import__("qrcode").QRCode(
            version=1,
            error_correction=__import__("qrcode").constants.ERROR_CORRECT_H,
            box_size=1,
            border=1,
        )
        qr.add_data(full_link)
        qr.make(fit=True)

        # Render ASCII art to a string first, then pipe through safe_print.
        # qrcode.print_ascii() writes directly to sys.stdout which bypasses
        # safe_print and can crash on Windows OEM codepages.
        ascii_buf = _io_mod.StringIO()
        # Handle both old qrcode (<9) using `out=` and newer using `target=`.
        import inspect

        sig = inspect.signature(qr.print_ascii)
        param_name = "target" if "target" in sig.parameters else "out"
        qr.print_ascii(**{param_name: ascii_buf}, invert=True)
        qr_text = ascii_buf.getvalue()

        safe_print("\n" + "=" * 50)
        safe_print("SCAN QR CODE TO CONNECT")
        safe_print("=" * 50)
        safe_print(qr_text)
        safe_print("=" * 50)
        safe_print(f"URL: {full_link}")
        safe_print("=" * 50 + "\n")
    except Exception as e:
        safe_print_stderr(f"[QR] Could not display QR code: {e}")
        safe_print(f"URL: {full_link}")


def save_qr_image(url: str, filename: str = "qr_code.png") -> None:
    """Save QR code as image file."""
    try:
        qr = __import__("qrcode").QRCode(
            version=1,
            error_correction=__import__("qrcode").constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image()
        img.save(filename)
        safe_print(f"[QR] Saved to {filename}")
    except Exception as e:
        safe_print_stderr(f"[QR] Could not save QR image: {e}")
