"""
Test cases for the Comparisons class over basic literal types.

Int, float, numpy array and BoundingBox comparisons are tested.
"""

import numpy as np
from holoviews.core import BoundingBox
from holoviews.element.comparison import ComparisonTestCase


class SimpleComparisonTest(ComparisonTestCase):

    def test_ints_equal(self):
        self.assertEqual(3,3)

    def test_ints_unequal(self):
        try:
            self.assertEqual(3,4)
        except AssertionError as e:
            self.assertEqual(str(e), "3 != 4")

    def test_floats_equal(self):
        self.assertEqual(3.5,3.5)

    def test_floats_unequal(self):
        try:
            self.assertEqual(3.5,4.5)
        except AssertionError as e:
            self.assertEqual(str(e)[:37], "Floats not almost equal to 6 decimals")

    def test_numpy_floats_equal(self):
        self.assertEqual(np.float32(3.5), np.float32(3.5))

    def test_numpy_floats_unequal(self):
        try:
            self.assertEqual(np.float32(3.5), np.float32(3.51))
        except AssertionError as e:
            self.assertEqual(str(e)[:37], "Floats not almost equal to 6 decimals")

    def test_float_heterogeneous_unequal1(self):
        try:
            self.assertEqual(np.float32(3.52),3.5)
        except AssertionError as e:
            self.assertEqual(str(e), "3.52 != 3.5")

    def test_float_heterogeneous_unequal2(self):
        try:
            self.assertEqual(np.float64(3.54),3.5)
        except AssertionError as e:
            self.assertEqual(str(e), "3.54 != 3.5")

    def test_float_heterogeneous_unequal3(self):
        try:
            self.assertEqual(np.float64(3.0), np.float32(4.0))
        except AssertionError as e:
            self.assertEqual(str(e), "3.0 != 4.0")

    def test_arrays_equal_int(self):
        self.assertEqual(np.array([[1,2],[3,4]]),
                         np.array([[1,2],[3,4]]))

    def test_floats_unequal_int(self):
        try:
            self.assertEqual(np.array([[1,2],[3,4]]),
                             np.array([[1,2],[3,5]]))
        except AssertionError as e:
            self.assertEqual(str(e)[:37], "Arrays not almost equal to 6 decimals")

    def test_arrays_equal_float(self):
        self.assertEqual(np.array([[1.0,2.5],[3,4]], dtype=np.float32),
                         np.array([[1.0,2.5],[3,4]], dtype=np.float32))

    def test_floats_unequal_float(self):
        try:
            self.assertEqual(np.array([[1,2],[3,4.5]], dtype=np.float32),
                             np.array([[1,2],[3,5]], dtype=np.float32))
        except AssertionError as e:
            self.assertEqual(str(e)[:37], "Arrays not almost equal to 6 decimals")

    def test_bounds_equal(self):
        self.assertEqual(BoundingBox(radius=0.5),
                         BoundingBox(radius=0.5))

    def test_bounds_unequal(self):
        try:
            self.assertEqual(BoundingBox(radius=0.5),
                             BoundingBox(radius=0.7))
        except AssertionError as e:
            self.assertEqual(str(e), "BoundingBox(radius=0.5) != BoundingBox(radius=0.7)")


    def test_bounds_equal_lbrt(self):
        self.assertEqual(BoundingBox(points=((-1,-1),(3,4.5))),
                         BoundingBox(points=((-1,-1),(3,4.5))))

    def test_bounds_unequal_lbrt(self):
        try:
            self.assertEqual(BoundingBox(points=((-1,-1),(3,4.5))),
                             BoundingBox(points=((-1,-1),(3,5.0))))
        except AssertionError as e:
            msg = 'BoundingBox(points=((-1,-1),(3,4.5))) != BoundingBox(points=((-1,-1),(3,5.0)))'
            self.assertEqual(str(e), msg)



if __name__ == "__main__":
    import sys
    import nose
    nose.runmodule(argv=[sys.argv[0], "--logging-level", "CRITICAL"])