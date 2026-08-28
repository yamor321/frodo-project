import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.concurrency import fetch_concurrently


class FetchConcurrentlyTests(unittest.TestCase):
    def test_preserves_input_order(self):
        tasks = [lambda i=i: i * 10 for i in range(20)]
        results = fetch_concurrently(tasks, max_workers=6)
        self.assertEqual(results, [i * 10 for i in range(20)])

    def test_a_failing_task_becomes_none_without_sinking_the_batch(self):
        def boom():
            raise ValueError("simulated download failure")

        tasks = [lambda: 1, boom, lambda: 3]
        results = fetch_concurrently(tasks, max_workers=3)
        self.assertEqual(results, [1, None, 3])

    def test_empty_task_list(self):
        self.assertEqual(fetch_concurrently([]), [])


if __name__ == "__main__":
    unittest.main()
