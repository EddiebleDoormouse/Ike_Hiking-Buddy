"""Prepare uploaded images for display and thumbnail storage."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
import pillow_heif

pillow_heif.register_heif_opener()


def _to_display_jpeg(data: bytes, max_px: int, filename: str) -> bytes:
    """Orient, resize, and encode image bytes as a metadata-free JPEG."""
    try:
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source)

            if "A" in image.getbands() or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba_image = image.convert("RGBA")
                background = Image.new("RGB", rgba_image.size, "white")
                background.paste(rgba_image, mask=rgba_image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            image.thumbnail((max_px, max_px), Image.LANCZOS)
            output = BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Could not read image {filename!r}: {exc}") from exc


def to_display_jpeg(data: bytes, filename: str, max_px: int = 1600) -> bytes:
    """Convert an uploaded image to an oriented, metadata-free display JPEG."""
    return _to_display_jpeg(data, max_px, filename)


def thumbnail(data: bytes, size: int = 400) -> bytes:
    """Create a metadata-free JPEG thumbnail without enlarging the image."""
    return _to_display_jpeg(data, size, "image")
