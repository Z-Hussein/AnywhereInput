"""Terminal QR code display for quick mobile access."""

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


def display_qr(url: str, token: str) -> None:
    """Display a QR code in the terminal for the given URL."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Terminal ASCII output
        print("\n" + "=" * 50)
        print("📱 SCAN QR CODE TO CONNECT")
        print("=" * 50)
        qr.print_ascii(invert=True)
        print("=" * 50)
        print(f"🔗 URL: {url}")
        print(f"🔑 Token: {token}")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"[QR] Could not display QR code: {e}")
        print(f"🔗 URL: {url}")
        print(f"🔑 Token: {token}")


def save_qr_image(url: str, filename: str = "qr_code.png") -> None:
    """Save QR code as image file."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer())
    img.save(filename)
    print(f"[QR] Saved to {filename}")
