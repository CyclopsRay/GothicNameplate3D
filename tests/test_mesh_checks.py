"""Exercise exported mesh rejection with small synthetic solids, without fonts."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mesh_checks import verify_glb_units, verify_stl


def write_wedge(path, missing_face=False):
    # A closed wedge whose outward upper face is 70 degrees above horizontal.
    height = 8 + 20 * np.tan(np.deg2rad(70))
    vertices = np.array([(0, 0, 0), (150, 0, 0), (150, 20, 0), (0, 20, 0),
                         (0, 0, 8), (150, 0, 8), (150, 20, height), (0, 20, height)])
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
    triangles = [(q[0], q[i], q[i + 1]) for q in quads for i in (1, 2)]
    if missing_face:
        triangles.pop()
    data = bytearray(80) + struct.pack('<I', len(triangles))
    for indices in triangles:
        data += struct.pack('<12fH', 0, 0, 0, *vertices[list(indices)].ravel(), 0)
    path.write_bytes(data)


class MeshCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'mesh.stl'

    def test_closed_solid_passes_round_trip(self):
        write_wedge(self.path)
        report = verify_stl(self.path, 150, 70)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['connected_components'], 1)

    def test_open_mesh_is_rejected(self):
        write_wedge(self.path, missing_face=True)
        with self.assertRaises(AssertionError):
            verify_stl(self.path, 150, 70)

    def test_incorrect_dimensions_are_rejected(self):
        write_wedge(self.path)
        with self.assertRaises(AssertionError):
            verify_stl(self.path, 180, 70)

    def test_incorrect_angle_is_rejected(self):
        write_wedge(self.path)
        with self.assertRaises(AssertionError):
            verify_stl(self.path, 150, 65)

    def test_glb_must_convert_millimeters_to_meters(self):
        for scale, valid in [([0.001] * 3, True), ([1] * 3, False)]:
            with self.subTest(scale=scale):
                data = json.dumps({'nodes': [{'mesh': 0, 'scale': scale}]}).encode()
                data += b' ' * (-len(data) % 4)
                self.path.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(data)) +
                                      struct.pack('<I4s', len(data), b'JSON') + data)
                if valid:
                    self.assertEqual(verify_glb_units(self.path)['status'], 'PASS')
                else:
                    with self.assertRaises(AssertionError):
                        verify_glb_units(self.path)


if __name__ == '__main__':
    unittest.main()
