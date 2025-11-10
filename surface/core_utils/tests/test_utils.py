from django.test import TestCase

from core_utils import utils


class Test(TestCase):
    def test_array_split(self):
        self.assertEqual(
            list(utils.array_split(list(range(12)), 10)),
            [[0, 1], [2, 3], [4], [5], [6], [7], [8], [9], [10], [11]],
        )
        self.assertEqual(
            list(utils.array_split(list(range(8)), 10)),
            [[0], [1], [2], [3], [4], [5], [6], [7]],
        )
        self.assertEqual(
            list(utils.array_split(list(range(10)), 10)),
            [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9]],
        )
        self.assertEqual(
            list(utils.array_split([], 10)),
            [],
        )
