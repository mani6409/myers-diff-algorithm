"""Myers O(ND) diff.

Usage:
    main.py lines     OLD_FILE NEW_FILE   # minimal line diff, old -> new
    main.py highlight OLD_FILE NEW_FILE   # same, plus changed-character ranges

How the program is organised (top to bottom):

    read_lines          file -> list of lines (raw bytes)
    intern_lines        lines -> small integers (fast comparison)
    find_edits          marks which old items are deleted, which new inserted
      myers_edits         divide and conquer driver around Myers' algorithm
        find_middle_snake   the heart of Myers' algorithm (forward + backward)
    walk_script         turns the marks into keep / change blocks
    format_ranges       turns character marks into "3-7,9-10" text
    highlight_line      builds the "? old | new" line for Part B
    run_diff            ties everything together and prints the result

Words used in the comments:
    old / new   the first / the second file (or line, or sequence of items)
    edit        one deletion from old or one insertion into new
    snake       a run of equal items that can be kept for free
    diagonal    old_position - new_position (explained above find_middle_snake)
"""
import sys


# ---------------------------------------------------------------------------
# Reading the input
# ---------------------------------------------------------------------------

def read_lines(path):
    """Return the lines of a file as a list of bytes objects.

    The file is read as raw bytes so that "\\r\\n" is NOT turned into "\\n"
    and invalid UTF-8 does not matter. A "\\r" stays part of its line.
    """
    with open(path, "rb") as file:
        file_content = file.read()

    lines = file_content.split(b"\n")

    # "a\nb\n" splits into ["a", "b", ""]. The last empty piece only means
    # "the file ended with a newline", so it is not a real line.
    # An empty file splits into [""], which becomes [] (no lines).
    if lines[-1] == b"":
        lines.pop()
    return lines


def intern_lines(old_lines, new_lines):
    """Replace every distinct line by a small integer.

    Equal lines get equal numbers, so later code can compare integers
    instead of byte strings, which is faster.
    """
    number_of_line = {}  # line -> its number

    def to_numbers(lines):
        return [number_of_line.setdefault(line, len(number_of_line))
                for line in lines]

    return to_numbers(old_lines), to_numbers(new_lines)


# ---------------------------------------------------------------------------
# Myers' algorithm
# ---------------------------------------------------------------------------
#
# Picture the "edit graph": a grid with the old items along one side and the
# new items along the other. We walk from the corner (0, 0) to the opposite
# corner (old_length, new_length).
#
# A position (old_position, new_position) means: the first old_position old
# items and the first new_position new items are already dealt with.
#
#   step right:    old_position + 1
#                  delete old_items[old_position]            costs 1 edit
#   step down:     new_position + 1
#                  insert new_items[new_position]            costs 1 edit
#   step diagonal: old_position + 1 and new_position + 1
#                  possible only if the two items are equal  free (keep it)
#
# The cheapest walk is a shortest edit script. Its number of right and down
# steps is the edit distance.
#
# The "diagonal" of a position is  old_position - new_position.
#   * a diagonal step keeps the diagonal number,
#   * a right step (delete) makes it one bigger,
#   * a down step (insert) makes it one smaller.
# After using exactly n edits you can only stand on the diagonals
#   -n, -n + 2, ..., n - 2, n.
#
# A "snake" is a run of free diagonal steps.

def find_middle_snake(old_items, old_start, old_length,
                      new_items, new_start, new_length):
    """Find the middle of a shortest edit path (linear-space Myers).

    Works on the slices
        old_items[old_start : old_start + old_length]  and
        new_items[new_start : new_start + new_length].

    Two searches run at the same time, each using about half of the edits:
      * a FORWARD search starting at the corner (0, 0), and
      * a BACKWARD search starting at the opposite corner
        (old_length, new_length) and walking back towards (0, 0).
    When they meet we have found a point on a shortest path.

    Returns (edit_distance, snake_start_old, snake_start_new,
             snake_end_old, snake_end_new):
    the number of edits on a shortest path, and the snake (a run of equal
    items) in the middle of it, given as positions relative to the start of
    the slices.
    """
    # The backward search starts on this diagonal (the opposite corner's).
    final_diagonal = old_length - new_length
    final_diagonal_is_odd = final_diagonal % 2 == 1

    # Each search needs at most this many edits before the two meet.
    max_edits_per_search = (old_length + new_length + 1) // 2

    # forward_reach[diagonal] = how far along the old items (old_position)
    # the forward search has got on that diagonal, using the current number
    # of edits. (new_position then follows: old_position - diagonal.)
    #
    # backward_reach[diagonal] = the same for the backward search, but
    # counted from the END of both slices: the number of old items consumed
    # from the end. The backward search is simply the forward search run on
    # the reversed sequences.
    #
    # A diagonal can be negative. Python counts a negative list index from
    # the end of the list, so forward_reach[-3] is just another free slot.
    # The lists are longer than 2 * max_edits_per_search + 3, so slots for
    # negative and positive diagonals never collide: no offset is needed.
    list_size = 2 * max_edits_per_search + 5
    forward_reach = [0] * list_size
    backward_reach = [0] * list_size

    old_last_index = old_start + old_length - 1   # last item of the old slice
    new_last_index = new_start + new_length - 1   # last item of the new slice

    for edits_used in range(max_edits_per_search + 1):

        # ---- Forward search: all paths using exactly edits_used edits ------
        for diagonal in range(-edits_used, edits_used + 1, 2):

            # Where does the best path to this diagonal come from?
            if diagonal == -edits_used:
                # Leftmost diagonal: can only come from the diagonal above by
                # a DOWN step (an insert), so old_position stays the same.
                old_position = forward_reach[diagonal + 1]
            elif diagonal == edits_used:
                # Rightmost diagonal: can only come from the diagonal below
                # by a RIGHT step (a delete), so old_position grows by one.
                old_position = forward_reach[diagonal - 1] + 1
            else:
                # Both neighbours are possible. Take the one that gets further.
                old_position_after_delete = forward_reach[diagonal - 1] + 1
                old_position_after_insert = forward_reach[diagonal + 1]
                old_position = max(old_position_after_delete,
                                   old_position_after_insert)
            new_position = old_position - diagonal

            # Follow the snake: keep equal items for free.
            snake_start_old = old_position
            snake_start_new = new_position
            while (old_position < old_length and new_position < new_length
                   and old_items[old_start + old_position]
                   == new_items[new_start + new_position]):
                old_position += 1
                new_position += 1
            forward_reach[diagonal] = old_position

            # Have the two searches met? Checked here only when
            # final_diagonal is odd: then the total number of edits is odd
            # (2 * edits_used - 1) and this forward path meets a backward path
            # that used one edit less. The backward search can only be on the
            # diagonal  final_diagonal - diagonal  and has only reached
            # diagonals closer than edits_used to final_diagonal.
            if (final_diagonal_is_odd
                    and final_diagonal - edits_used < diagonal
                    and diagonal < final_diagonal + edits_used
                    and old_position + backward_reach[final_diagonal - diagonal]
                    >= old_length):
                return (2 * edits_used - 1,
                        snake_start_old, snake_start_new,
                        old_position, new_position)

        # ---- Backward search: the same, on the reversed sequences ----------
        # Here old_position counts old items taken from the END of the old
        # slice, and new_position counts new items taken from the END of the
        # new slice.
        for diagonal in range(-edits_used, edits_used + 1, 2):
            if diagonal == -edits_used:
                old_position = backward_reach[diagonal + 1]
            elif diagonal == edits_used:
                old_position = backward_reach[diagonal - 1] + 1
            else:
                old_position_after_delete = backward_reach[diagonal - 1] + 1
                old_position_after_insert = backward_reach[diagonal + 1]
                old_position = max(old_position_after_delete,
                                   old_position_after_insert)
            new_position = old_position - diagonal

            reversed_snake_start_old = old_position
            reversed_snake_start_new = new_position
            while (old_position < old_length and new_position < new_length
                   and old_items[old_last_index - old_position]
                   == new_items[new_last_index - new_position]):
                old_position += 1
                new_position += 1
            backward_reach[diagonal] = old_position

            # Have the two searches met? Checked here only when
            # final_diagonal is even: then the total number of edits is even
            # (2 * edits_used) and this backward path meets a forward path
            # that used the same number of edits.
            if (not final_diagonal_is_odd
                    and -edits_used <= final_diagonal - diagonal
                    and final_diagonal - diagonal <= edits_used
                    and old_position + forward_reach[final_diagonal - diagonal]
                    >= old_length):
                # Convert the snake from "counted from the end" back to normal
                # positions: a position p counted from the end is position
                # (length - p) counted from the start. The snake therefore
                # runs from where the reversed snake ended to where it began.
                return (2 * edits_used,
                        old_length - old_position,
                        new_length - new_position,
                        old_length - reversed_snake_start_old,
                        new_length - reversed_snake_start_new)

    raise AssertionError("middle snake not found")  # cannot happen


def myers_edits(old_items, new_items):
    """Mark a minimal set of edits turning old_items into new_items.

    Returns two lists of booleans:
      old_is_deleted[i]   True when old_items[i] must be deleted
      new_is_inserted[j]  True when new_items[j] must be inserted
    Everything not marked is kept, and the kept old items equal the kept
    new items, in the same order.

    The problem is split in two at the middle snake, again and again, until
    the pieces are trivial. A stack of pending pieces replaces recursion.
    """
    old_is_deleted = [False] * len(old_items)
    new_is_inserted = [False] * len(new_items)

    # A piece of work is a range of the old items and a range of the new
    # items (an end is exclusive):  (old_begin, old_end, new_begin, new_end)
    pending_pieces = [(0, len(old_items), 0, len(new_items))]

    while pending_pieces:
        old_begin, old_end, new_begin, new_end = pending_pieces.pop()

        # Items equal at the start of both ranges can simply be kept.
        while (old_begin < old_end and new_begin < new_end
               and old_items[old_begin] == new_items[new_begin]):
            old_begin += 1
            new_begin += 1
        # So can items equal at the end of both ranges.
        while (old_begin < old_end and new_begin < new_end
               and old_items[old_end - 1] == new_items[new_end - 1]):
            old_end -= 1
            new_end -= 1

        # One range is empty: everything left in the other range is an edit.
        if old_begin == old_end:
            for new_index in range(new_begin, new_end):
                new_is_inserted[new_index] = True
            continue
        if new_begin == new_end:
            for old_index in range(old_begin, old_end):
                old_is_deleted[old_index] = True
            continue

        # Both ranges still have items, their first items differ and their
        # last items differ, so at least 2 edits are needed. Split at the
        # middle snake. The snake itself is a run of equal items (kept), so
        # only the part before it and the part after it remain to be solved.
        (_, snake_start_old, snake_start_new,
         snake_end_old, snake_end_new) = find_middle_snake(
            old_items, old_begin, old_end - old_begin,
            new_items, new_begin, new_end - new_begin)
        part_before_snake = (old_begin, old_begin + snake_start_old,
                             new_begin, new_begin + snake_start_new)
        part_after_snake = (old_begin + snake_end_old, old_end,
                            new_begin + snake_end_new, new_end)
        pending_pieces.append(part_before_snake)
        pending_pieces.append(part_after_snake)

    return old_is_deleted, new_is_inserted


def find_edits(old_items, new_items):
    """Return (old_is_deleted, new_is_inserted) for a minimal edit script.

    Speed-up before running Myers: an item that occurs in only one of the two
    sequences can never be matched, so it is certainly deleted (or inserted).
    Marking those directly and running Myers on the rest gives the same
    minimal result, because removing unmatchable items does not change the
    longest common subsequence.
    """
    items_in_old = set(old_items)
    items_in_new = set(new_items)

    # Positions of the items that exist in both sequences.
    shared_old_positions = [old_index
                            for old_index, item in enumerate(old_items)
                            if item in items_in_new]
    shared_new_positions = [new_index
                            for new_index, item in enumerate(new_items)
                            if item in items_in_old]

    # Start by assuming every item is an edit ...
    old_is_deleted = [True] * len(old_items)
    new_is_inserted = [True] * len(new_items)

    # ... then let Myers decide about the shared items only.
    shared_old_is_deleted, shared_new_is_inserted = myers_edits(
        [old_items[old_index] for old_index in shared_old_positions],
        [new_items[new_index] for new_index in shared_new_positions])
    for shared_index, old_index in enumerate(shared_old_positions):
        old_is_deleted[old_index] = shared_old_is_deleted[shared_index]
    for shared_index, new_index in enumerate(shared_new_positions):
        new_is_inserted[new_index] = shared_new_is_inserted[shared_index]
    return old_is_deleted, new_is_inserted


# ---------------------------------------------------------------------------
# Turning the marks into output
# ---------------------------------------------------------------------------

def walk_script(old_is_deleted, new_is_inserted):
    """Walk through the marks and yield the edit script block by block.

    Yields:
      ("keep", old_index, new_index)
          old line old_index equals new line new_index
      ("change", delete_start, delete_end, insert_start, insert_end)
          delete old lines [delete_start:delete_end] and
          insert new lines [insert_start:insert_end]

    A change block is a group of consecutive deletions and insertions with
    no kept line between them. Because the block is returned as "all
    deletions, then all insertions", the caller prints every "-" line before
    any "+" line (the delete-first rule).
    """
    old_index = 0
    new_index = 0
    while old_index < len(old_is_deleted) or new_index < len(new_is_inserted):
        old_is_kept = (old_index < len(old_is_deleted)
                       and not old_is_deleted[old_index])
        new_is_kept = (new_index < len(new_is_inserted)
                       and not new_is_inserted[new_index])
        if old_is_kept and new_is_kept:
            yield ("keep", old_index, new_index)
            old_index += 1
            new_index += 1
            continue

        # A change block starts here: take all deletions, then all insertions.
        delete_start = old_index
        insert_start = new_index
        while old_index < len(old_is_deleted) and old_is_deleted[old_index]:
            old_index += 1
        while new_index < len(new_is_inserted) and new_is_inserted[new_index]:
            new_index += 1
        yield ("change", delete_start, old_index, insert_start, new_index)


def format_ranges(is_marked):
    """Turn a list of booleans into text like "3-7,9-10", or "." if none.

    A range "start-end" covers the positions start .. end-1. Neighbouring
    True values form one range, so touching ranges are merged automatically.
    """
    range_texts = []
    position = 0
    while position < len(is_marked):
        if is_marked[position]:
            range_start = position
            while position < len(is_marked) and is_marked[position]:
                position += 1
            range_texts.append("%d-%d" % (range_start, position))
        else:
            position += 1
    return ",".join(range_texts) if range_texts else "."


def highlight_line(old_line, new_line):
    """Return the "? old_ranges | new_ranges" line for a changed line pair.

    The same diff routine is used, but on the characters of the two lines.
    Decoding to str first makes each position one Unicode code point.
    "surrogateescape" keeps any invalid byte from crashing the program.
    """
    old_text = old_line.decode("utf-8", "surrogateescape")
    new_text = new_line.decode("utf-8", "surrogateescape")
    old_char_is_deleted, new_char_is_inserted = find_edits(old_text, new_text)
    highlight_text = "? %s | %s\n" % (format_ranges(old_char_is_deleted),
                                      format_ranges(new_char_is_inserted))
    return highlight_text.encode("utf-8", "surrogateescape")


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------

def run_diff(mode, old_path, new_path):
    """Print the diff of two files. Returns the process exit code."""
    try:
        old_lines = read_lines(old_path)
        new_lines = read_lines(new_path)
    except OSError as error:
        sys.stderr.write("error: %s\n" % error)
        return 2   # unreadable file: nothing on stdout, exit code 2

    old_numbers, new_numbers = intern_lines(old_lines, new_lines)
    old_is_deleted, new_is_inserted = find_edits(old_numbers, new_numbers)

    output_pieces = []
    for block in walk_script(old_is_deleted, new_is_inserted):
        if block[0] == "keep":
            _, old_index, _ = block
            output_pieces.append(b" " + old_lines[old_index] + b"\n")
            continue

        _, delete_start, delete_end, insert_start, insert_end = block
        for old_index in range(delete_start, delete_end):
            output_pieces.append(b"-" + old_lines[old_index] + b"\n")
        for new_index in range(insert_start, insert_end):
            output_pieces.append(b"+" + new_lines[new_index] + b"\n")

            # Part B: the 1st "+" line of the block pairs with the 1st "-"
            # line, the 2nd with the 2nd, and so on. A "+" line with no
            # partner (more insertions than deletions) gets no extra line.
            partner_index = delete_start + (new_index - insert_start)
            if mode == "highlight" and partner_index < delete_end:
                output_pieces.append(highlight_line(
                    old_lines[partner_index], new_lines[new_index]))

    sys.stdout.buffer.write(b"".join(output_pieces))
    return 0


def main(argv):
    if len(argv) != 4 or argv[1] not in ("lines", "highlight"):
        sys.stderr.write("usage: main.py lines|highlight OLD_FILE NEW_FILE\n")
        return 2
    return run_diff(argv[1], argv[2], argv[3])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
