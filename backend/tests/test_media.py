"""Tests for image conversion and thumbnail creation."""

from io import BytesIO

import pytest
from PIL import Image

from app.services.images import thumbnail, to_display_jpeg


# --- images.py ---

def test_to_display_jpeg_applies_orientation_and_strips_metadata():
    source = Image.new("RGB", (3000, 2000), "navy")
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x8825] = {
        1: "N",
        2: (51.5, 30.0, 0.0),
        3: "W",
        4: (0.0, 7.0, 0.0),
    }
    source_buffer = BytesIO()
    source.save(source_buffer, format="JPEG", exif=exif)
    with Image.open(BytesIO(source_buffer.getvalue())) as original:
        assert original.getexif().get_ifd(0x8825)

    output = to_display_jpeg(source_buffer.getvalue(), "hike.jpg")

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert image.height == 1600
        assert image.width < image.height
        assert image.getexif() == {}
        assert 0x8825 not in image.getexif()
        assert 0x0112 not in image.getexif()
        assert "icc_profile" not in image.info


def test_to_display_jpeg_reads_heic_without_upscaling():
    source = Image.new("RGB", (320, 240), "forestgreen")
    source_buffer = BytesIO()
    source.save(source_buffer, format="HEIF")

    output = to_display_jpeg(source_buffer.getvalue(), "hike.heic")

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert image.size == (320, 240)


def test_to_display_jpeg_converts_rgba_png_to_rgb_jpeg():
    source = Image.new("RGBA", (80, 60), (255, 0, 0, 128))
    source_buffer = BytesIO()
    source.save(source_buffer, format="PNG")

    output = to_display_jpeg(source_buffer.getvalue(), "overlay.png")

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_thumbnail_resizes_longest_side_to_size():
    source = Image.new("RGB", (1200, 800), "darkgreen")
    source_buffer = BytesIO()
    source.save(source_buffer, format="JPEG")

    output = thumbnail(source_buffer.getvalue(), 400)

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == 400


def test_to_display_jpeg_rejects_garbage_bytes():
    with pytest.raises(ValueError, match="Could not read image 'broken.jpg'"):
        to_display_jpeg(b"not an image", "broken.jpg")
