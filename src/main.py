"""Myers O(ND) diff: `lines A B` and `highlight A B`."""
import sys


def read_lines(path):
    with open(path, "rb") as f:
        data = f.read()
    parts = data.split(b"\n")
    if parts[-1] == b"":
        parts.pop()
    return parts


def middle_snake(a, alo, N, b, blo, M):
    """Myers' linear-space middle snake on a[alo:alo+N], b[blo:blo+M].

    Returns (D, xs, ys, xe, ye): the snake runs (xs, ys) -> (xe, ye) in
    coordinates relative to alo/blo, and D is the edit distance.
    Diagonals index the V arrays directly; negative k wraps around, which is
    safe because the arrays are longer than 2*max+3.
    """
    delta = N - M
    odd = delta & 1
    half = (N + M + 1) // 2
    size = 2 * half + 5
    vf = [0] * size
    vb = [0] * size
    ra_end = alo + N - 1
    rb_end = blo + M - 1
    for d in range(half + 1):
        # forward pass
        for k in range(-d, d + 1, 2):
            if k == -d:
                x = vf[k + 1]
            elif k == d:
                x = vf[k - 1] + 1
            else:
                lo = vf[k - 1]
                hi = vf[k + 1]
                x = hi if lo < hi else lo + 1
            y = x - k
            x0 = x
            y0 = y
            while x < N and y < M and a[alo + x] == b[blo + y]:
                x += 1
                y += 1
            vf[k] = x
            if odd and delta - d < k < delta + d and x + vb[delta - k] >= N:
                return 2 * d - 1, x0, y0, x, y
        # backward pass (on reversed sequences)
        for k in range(-d, d + 1, 2):
            if k == -d:
                x = vb[k + 1]
            elif k == d:
                x = vb[k - 1] + 1
            else:
                lo = vb[k - 1]
                hi = vb[k + 1]
                x = hi if lo < hi else lo + 1
            y = x - k
            x0 = x
            y0 = y
            while x < N and y < M and a[ra_end - x] == b[rb_end - y]:
                x += 1
                y += 1
            vb[k] = x
            if not odd and -d <= delta - k <= d and x + vf[delta - k] >= N:
                return 2 * d, N - x, M - y, N - x0, M - y0
    raise AssertionError("middle snake not found")


def diff_flags(a, b):
    """Return (del_a, ins_b) boolean lists for a minimal edit script.

    Items present in only one sequence can never match, so they are flagged
    directly and only the remaining items go through Myers. This keeps the
    result minimal while shrinking N, M (and often D).
    """
    in_a = set(a)
    in_b = set(b)
    idx_a = [i for i, x in enumerate(a) if x in in_b]
    idx_b = [j for j, x in enumerate(b) if x in in_a]
    del_a = [True] * len(a)
    ins_b = [True] * len(b)
    fa = [a[i] for i in idx_a]
    fb = [b[j] for j in idx_b]
    fd, fi = _myers_flags(fa, fb)
    for t, i in enumerate(idx_a):
        del_a[i] = fd[t]
    for t, j in enumerate(idx_b):
        ins_b[j] = fi[t]
    return del_a, ins_b


def _myers_flags(a, b):
    n, m = len(a), len(b)
    del_a = [False] * n
    ins_b = [False] * m
    stack = [(0, n, 0, m)]
    while stack:
        alo, ahi, blo, bhi = stack.pop()
        while alo < ahi and blo < bhi and a[alo] == b[blo]:
            alo += 1
            blo += 1
        while alo < ahi and blo < bhi and a[ahi - 1] == b[bhi - 1]:
            ahi -= 1
            bhi -= 1
        if alo == ahi:
            for j in range(blo, bhi):
                ins_b[j] = True
            continue
        if blo == bhi:
            for i in range(alo, ahi):
                del_a[i] = True
            continue
        _, xs, ys, xe, ye = middle_snake(a, alo, ahi - alo, b, blo, bhi - blo)
        stack.append((alo, alo + xs, blo, blo + ys))
        stack.append((alo + xe, ahi, blo + ye, bhi))
    return del_a, ins_b


def intern(a, b):
    table = {}
    ia = [table.setdefault(s, len(table)) for s in a]
    ib = [table.setdefault(s, len(table)) for s in b]
    return ia, ib


def blocks(del_a, ins_b):
    """Yield ('keep', i, j) or ('change', i0, i1, j0, j1), delete-first."""
    n, m = len(del_a), len(ins_b)
    i = j = 0
    while i < n or j < m:
        if i < n and j < m and not del_a[i] and not ins_b[j]:
            yield ("keep", i, j)
            i += 1
            j += 1
            continue
        i0, j0 = i, j
        while i < n and del_a[i]:
            i += 1
        while j < m and ins_b[j]:
            j += 1
        yield ("change", i0, i, j0, j)


def ranges(flags):
    out = []
    i, n = 0, len(flags)
    while i < n:
        if flags[i]:
            s = i
            while i < n and flags[i]:
                i += 1
            out.append("%d-%d" % (s, i))
        else:
            i += 1
    return ",".join(out) if out else "."


def decode(line):
    return line.decode("utf-8", "surrogateescape")


def run(mode, path_a, path_b):
    try:
        a = read_lines(path_a)
        b = read_lines(path_b)
    except OSError as e:
        sys.stderr.write("error: %s\n" % e)
        return 2
    ia, ib = intern(a, b)
    del_a, ins_b = diff_flags(ia, ib)
    out = []
    add = out.append
    for blk in blocks(del_a, ins_b):
        if blk[0] == "keep":
            add(b" " + a[blk[1]] + b"\n")
            continue
        _, i0, i1, j0, j1 = blk
        for i in range(i0, i1):
            add(b"-" + a[i] + b"\n")
        for j in range(j0, j1):
            add(b"+" + b[j] + b"\n")
            if mode == "highlight" and j - j0 < i1 - i0:
                old = decode(a[i0 + j - j0])
                new = decode(b[j])
                da, db = diff_flags(old, new)
                add(("? %s | %s\n" % (ranges(da), ranges(db)))
                    .encode("utf-8", "surrogateescape"))
    sys.stdout.buffer.write(b"".join(out))
    return 0


def main(argv):
    if len(argv) != 4 or argv[1] not in ("lines", "highlight"):
        sys.stderr.write("usage: main.py lines|highlight A B\n")
        return 2
    return run(argv[1], argv[2], argv[3])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
