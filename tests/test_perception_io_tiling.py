import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agri_intelligence.perception.contracts import ImageFrame
from agri_intelligence.perception.image_io import ImageDecodeError, read_image
from agri_intelligence.perception.tiling import generate_tiles


SHA = "b" * 64


def frame(width=5, height=4, channels=1, pixels=None):
    if pixels is None:
        pixels = bytes(range(width * height * channels))
    return ImageFrame(
        image_id="fixture",
        width=width,
        height=height,
        channels=channels,
        dtype="uint8",
        color_space="GRAY" if channels == 1 else "RGB",
        source_sha256=SHA,
        pixels=pixels,
    )


class TilingTests(unittest.TestCase):
    def test_tiles_cover_image_and_are_row_major(self):
        source = frame()
        tiles = generate_tiles(source, tile_width=3, tile_height=2)
        records = [record for _, record in tiles]
        self.assertEqual([(r.x, r.y) for r in records], [(0, 0), (2, 0), (0, 2), (2, 2)])
        self.assertEqual([r.tile_index for r in records], [0, 1, 2, 3])
        self.assertTrue(all(r.image_id == "fixture" for r in records))

    def test_overlap_and_edge_alignment_are_deterministic(self):
        source = frame(width=11, height=7)
        first = generate_tiles(source, tile_width=5, tile_height=4, overlap=2)
        second = generate_tiles(source, tile_width=5, tile_height=4, overlap=2)
        self.assertEqual(
            [(r.x, r.y, r.width, r.height) for _, r in first],
            [(r.x, r.y, r.width, r.height) for _, r in second],
        )
        xs = sorted({r.x for _, r in first})
        ys = sorted({r.y for _, r in first})
        self.assertEqual(xs[-1] + 5, 11)
        self.assertEqual(ys[-1] + 4, 7)

    def test_image_smaller_than_tile_produces_one_native_size_tile(self):
        tiles = generate_tiles(frame(width=2, height=3), tile_width=8, tile_height=9)
        self.assertEqual(len(tiles), 1)
        tile, record = tiles[0]
        self.assertEqual((tile.width, tile.height), (2, 3))
        self.assertEqual((record.x, record.y, record.width, record.height), (0, 0, 2, 3))

    def test_odd_dimensions_preserve_all_edge_pixels(self):
        source = frame(width=7, height=5)
        tiles = generate_tiles(source, tile_width=4, tile_height=3, overlap=1)
        self.assertEqual(max(r.x + r.width for _, r in tiles), 7)
        self.assertEqual(max(r.y + r.height for _, r in tiles), 5)

    def test_tile_pixels_are_exact_row_major_crops(self):
        source = frame(width=4, height=3)
        tiles = generate_tiles(source, tile_width=2, tile_height=2)
        top_right, record = tiles[1]
        self.assertEqual((record.x, record.y), (2, 0))
        self.assertEqual(top_right.pixels, bytes([2, 3, 6, 7]))
        bottom_left, _ = tiles[2]
        self.assertEqual(bottom_left.pixels, bytes([8, 9, 12, 13]))

    def test_tile_frames_preserve_source_provenance(self):
        source = frame()
        tile, record = generate_tiles(source, tile_width=3, tile_height=2)[0]
        self.assertEqual(tile.source_sha256, source.source_sha256)
        self.assertEqual(tile.image_id, source.image_id)
        self.assertEqual(tile.tile_id, record.tile_id)

    def test_invalid_tile_configuration_is_rejected(self):
        for kwargs in (
            {"tile_width": 0, "tile_height": 2},
            {"tile_width": 2, "tile_height": -1},
            {"tile_width": 2, "tile_height": 2, "overlap": -1},
            {"tile_width": 2, "tile_height": 2, "overlap": 2},
        ):
            with self.assertRaises(ValueError):
                generate_tiles(frame(), **kwargs)

    def test_mutable_or_inconsistent_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            generate_tiles(frame(pixels=bytearray(20)), tile_width=2, tile_height=2)
        with self.assertRaises(ValueError):
            generate_tiles(frame(pixels=b"short"), tile_width=2, tile_height=2)

    def test_nested_tiling_is_rejected(self):
        parent = frame()
        tile, _ = generate_tiles(parent, tile_width=3, tile_height=2)[0]
        with self.assertRaises(ValueError):
            generate_tiles(tile, tile_width=2, tile_height=2)


class ImageIOTests(unittest.TestCase):
    def test_missing_file_fails_with_domain_error(self):
        with self.assertRaises(ImageDecodeError):
            read_image(Path("/path/that/does/not/exist.png"))

    def test_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ImageDecodeError):
                read_image(Path(directory))

    def test_pixel_limit_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-an-image.png"
            path.write_bytes(b"not an image")
            with self.assertRaises(ValueError):
                read_image(path, max_pixels=0)

    def test_symlink_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.png"
            target.write_bytes(b"placeholder")
            link = root / "link.png"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ImageDecodeError):
                read_image(link)


if __name__ == "__main__":
    unittest.main()
