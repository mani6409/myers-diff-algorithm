import os
import random
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "..", "src", "main.py")
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import main as myers  # noqa: E402


def lcs_len(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def check(test, a, b):
    da, ib = myers.find_edits(a, b)
    ka = [x for x, f in zip(a, da) if not f]
    kb = [x for x, f in zip(b, ib) if not f]
    test.assertEqual(ka, kb)
    test.assertEqual(len(ka), lcs_len(a, b))


class DiffFlags(unittest.TestCase):
    def test_paper_example(self):
        a, b = list("abcabba"), list("cbabac")
        da, ib = myers.find_edits(a, b)
        self.assertEqual(sum(da) + sum(ib), 5)
        check(self, a, b)

    def test_edges(self):
        for a, b in [("", ""), ("", "abc"), ("abc", ""), ("abc", "abc"),
                     ("a", "b"), ("ab", "ba"), ("aaaa", "aa")]:
            check(self, list(a), list(b))

    def test_random_minimal(self):
        rnd = random.Random(1)
        for _ in range(3000):
            a = [rnd.randint(0, 3) for _ in range(rnd.randint(0, 12))]
            b = [rnd.randint(0, 3) for _ in range(rnd.randint(0, 12))]
            check(self, a, b)


def run_cli(mode, a, b):
    with tempfile.TemporaryDirectory() as d:
        pa, pb = os.path.join(d, "a"), os.path.join(d, "b")
        for path, data in ((pa, a), (pb, b)):
            with open(path, "wb") as f:
                f.write(data)
        return subprocess.run([sys.executable, MAIN, mode, pa, pb],
                              capture_output=True)


class Cli(unittest.TestCase):
    def test_delete_first(self):
        r = run_cli("lines", b"a\nb\nc\n", b"a\nx\nc\n")
        self.assertEqual(r.stdout, b" a\n-b\n+x\n c\n")

    def test_empty(self):
        self.assertEqual(run_cli("lines", b"", b"").stdout, b"")

    def test_crlf_distinct(self):
        r = run_cli("lines", b"a\r\n", b"a\n")
        self.assertEqual(r.stdout, b"-a\r\n+a\n")

    def test_missing_file(self):
        r = subprocess.run([sys.executable, MAIN, "lines", "/nope", "/nope"],
                           capture_output=True)
        self.assertEqual((r.returncode, r.stdout), (2, b""))

    def test_highlight_examples(self):
        r = run_cli("highlight", b"a = 1\nb = 2\n", b"a = 10\n")
        self.assertEqual(r.stdout, b"-a = 1\n-b = 2\n+a = 10\n? . | 5-6\n")
        r = run_cli("highlight", "hi \U0001F600\n".encode(),
                    "hi \U0001F603\n".encode())
        self.assertTrue(r.stdout.endswith(b"? 3-4 | 3-4\n"))

    def test_invalid_utf8_lines(self):
        r = run_cli("lines", b"\xff\nx\n", b"\xfe\nx\n")
        self.assertEqual(r.stdout, b"-\xff\n+\xfe\n x\n")


if __name__ == "__main__":
    unittest.main()
