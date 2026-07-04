"""Terminal QR code display for quick mobile access."""

import qrcode

# Lazy import for styled QR — will gracefully fail on headless/minimal installs
_styled_imported = False
try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    _styled_imported = True
except Exception:
    pass


def display_qr(url: str, token: str) -> None:
    """Display a QR code in the terminal for the given URL.

    The QR encodes the full client link with the token baked in,
    so scanning auto-fills both server and token fields.
    """
    # Build the full client URL with token embedded
    full_link = f"{url}/?token={token}"
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=1,
            border=1,
        )
        qr.add_data(full_link)
        qr.make(fit=True)

        # Terminal ASCII output
        print("\n" + "=" * 50)
        print("📱 SCAN QR CODE TO CONNECT")
        print("=" * 50)
        qr.print_ascii(invert=True)
        print("=" * 50)
        print(f"🔗 URL: {full_link}")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"[QR] Could not display QR code: {e}")
        print(f"🔗 URL: {full_link}")


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

    img = qr.make_image() if not _styled_imported else qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer())
    img.save(filename)
    print(f"[QR] Saved to {filename}")
"""Terminal QR code display for quick mobile access."""

import qrcode

# Lazy import for styled QR — will gracefully fail on headless/minimal installs
_styled_imported = False
try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    _styled_imported = True
except Exception:
    pass


def display_qr(url: str, token: str) -> None:
    """Display a QR code in the terminal for the given URL.

    The QR encodes the full client link with the token baked in,
    so scanning auto-fills both server and token fields.
    """
    # Build the full client URL with ability to add token embedding
    full_link = f"{url}/" # add ?token={token} after {url}/ to auto fill the token input
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=1,
            border=1,
        )
        qr.add_data(full_link)
        qr.make(fit=True)

        # Terminal ASCII output
        print("\n" + "=" * 50)
        print("📱 SCAN QR CODE TO CONNECT")
        print("=" * 50)
        qr.print_ascii(invert=True)
        print("=" * 50)
        print(f"🔗 URL: {full_link}")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"[QR] Could not display QR code: {e}")
        print(f"🔗 URL: {full_link}")


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

    img = qr.make_image() if not _styled_imported else qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer())
    img.save(filename)
    print(f"[QR] Saved to {filename}")
