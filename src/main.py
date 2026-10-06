"""Minimal line diff (Myers' O(ND) algorithm) with character highlighting.

    main.py lines     OLD_FILE NEW_FILE
    main.py highlight OLD_FILE NEW_FILE
"""
import sys


def read_lines(path):
    """Read a file as bytes and split it into lines ("\\r" stays in the line)."""
    with open(path, "rb") as file:
        lines = file.read().split(b"\n")
    if lines[-1] == b"":  # the file ended with a newline (or was empty)
        lines.pop()
    return lines


def intern_lines(old_lines, new_lines):
    """Map equal lines to equal integers so they compare quickly."""
    number_of_line = {}

    def to_numbers(lines):
        return [number_of_line.setdefault(line, len(number_of_line))
                for line in lines]

    return to_numbers(old_lines), to_numbers(new_lines)


# Myers' algorithm walks an "edit graph" from (0, 0) to (old_length,
# new_length). A step right deletes an old item, a step down inserts a new
# item, and a diagonal step keeps an item that is equal in both (free).
# A position's diagonal is old_position - new_position. A run of diagonal
# steps is called a snake.

def find_middle_snake(old_items, old_start, old_length,
                      new_items, new_start, new_length):
    """Search forward from the start and backward from the end until the two
    searches meet. Returns (edit_distance, snake_start_old, snake_start_new,
    snake_end_old, snake_end_new), with positions relative to the slices
    old_items[old_start:old_start + old_length] and
    new_items[new_start:new_start + new_length].
    """
    final_diagonal = old_length - new_length
    final_diagonal_is_odd = final_diagonal % 2 == 1
    max_edits_per_search = (old_length + new_length + 1) // 2

    # reach[diagonal] is the furthest old_position found on that diagonal.
    # The backward search runs on the reversed sequences, so its positions
    # count items from the end. Negative diagonals index from the end of the
    # list, which is fine because the lists are long enough not to overlap.
    list_size = 2 * max_edits_per_search + 5
    forward_reach = [0] * list_size
    backward_reach = [0] * list_size

    old_last_index = old_start + old_length - 1
    new_last_index = new_start + new_length - 1

    for edits_used in range(max_edits_per_search + 1):

        # Forward search
        for diagonal in range(-edits_used, edits_used + 1, 2):
            if diagonal == -edits_used:
                old_position = forward_reach[diagonal + 1]
            elif diagonal == edits_used:
                old_position = forward_reach[diagonal - 1] + 1
            else:
                old_position = max(forward_reach[diagonal - 1] + 1,
                                   forward_reach[diagonal + 1])
            new_position = old_position - diagonal

            snake_start_old = old_position
            snake_start_new = new_position
            while (old_position < old_length and new_position < new_length
                   and old_items[old_start + old_position]
                   == new_items[new_start + new_position]):
                old_position += 1
                new_position += 1
            forward_reach[diagonal] = old_position

            # With an odd final diagonal the two searches meet here.
            if (final_diagonal_is_odd
                    and final_diagonal - edits_used < diagonal
                    and diagonal < final_diagonal + edits_used
                    and old_position + backward_reach[final_diagonal - diagonal]
                    >= old_length):
                return (2 * edits_used - 1,
                        snake_start_old, snake_start_new,
                        old_position, new_position)

        # Backward search
        for diagonal in range(-edits_used, edits_used + 1, 2):
            if diagonal == -edits_used:
                old_position = backward_reach[diagonal + 1]
            elif diagonal == edits_used:
                old_position = backward_reach[diagonal - 1] + 1
            else:
                old_position = max(backward_reach[diagonal - 1] + 1,
                                   backward_reach[diagonal + 1])
            new_position = old_position - diagonal

            reversed_snake_start_old = old_position
            reversed_snake_start_new = new_position
            while (old_position < old_length and new_position < new_length
                   and old_items[old_last_index - old_position]
                   == new_items[new_last_index - new_position]):
                old_position += 1
                new_position += 1
            backward_reach[diagonal] = old_position

            # With an even final diagonal the two searches meet here.
            if (not final_diagonal_is_odd
                    and -edits_used <= final_diagonal - diagonal
                    and final_diagonal - diagonal <= edits_used
                    and old_position + forward_reach[final_diagonal - diagonal]
                    >= old_length):
                # Convert positions counted from the end back to normal ones.
                return (2 * edits_used,
                        old_length - old_position,
                        new_length - new_position,
                        old_length - reversed_snake_start_old,
                        new_length - reversed_snake_start_new)

    raise AssertionError("middle snake not found")


def myers_edits(old_items, new_items):
    """Return (old_is_deleted, new_is_inserted) for a minimal edit script.

    Splits the problem at the middle snake until the pieces are trivial.
    """
    old_is_deleted = [False] * len(old_items)
    new_is_inserted = [False] * len(new_items)

    # Each piece is (old_begin, old_end, new_begin, new_end), ends exclusive.
    pending_pieces = [(0, len(old_items), 0, len(new_items))]

    while pending_pieces:
        old_begin, old_end, new_begin, new_end = pending_pieces.pop()

        # Skip the common start and the common end.
        while (old_begin < old_end and new_begin < new_end
               and old_items[old_begin] == new_items[new_begin]):
            old_begin += 1
            new_begin += 1
        while (old_begin < old_end and new_begin < new_end
               and old_items[old_end - 1] == new_items[new_end - 1]):
            old_end -= 1
            new_end -= 1

        if old_begin == old_end:
            for new_index in range(new_begin, new_end):
                new_is_inserted[new_index] = True
            continue
        if new_begin == new_end:
            for old_index in range(old_begin, old_end):
                old_is_deleted[old_index] = True
            continue

        (_, snake_start_old, snake_start_new,
         snake_end_old, snake_end_new) = find_middle_snake(
            old_items, old_begin, old_end - old_begin,
            new_items, new_begin, new_end - new_begin)
        pending_pieces.append((old_begin, old_begin + snake_start_old,
                               new_begin, new_begin + snake_start_new))
        pending_pieces.append((old_begin + snake_end_old, old_end,
                               new_begin + snake_end_new, new_end))

    return old_is_deleted, new_is_inserted


def find_edits(old_items, new_items):
    """Like myers_edits, but items found in only one sequence are marked
    directly: they can never match, so Myers only needs the shared items.
    """
    items_in_old = set(old_items)
    items_in_new = set(new_items)
    shared_old_positions = [index for index, item in enumerate(old_items)
                            if item in items_in_new]
    shared_new_positions = [index for index, item in enumerate(new_items)
                            if item in items_in_old]

    old_is_deleted = [True] * len(old_items)
    new_is_inserted = [True] * len(new_items)

    shared_old_is_deleted, shared_new_is_inserted = myers_edits(
        [old_items[index] for index in shared_old_positions],
        [new_items[index] for index in shared_new_positions])
    for shared_index, old_index in enumerate(shared_old_positions):
        old_is_deleted[old_index] = shared_old_is_deleted[shared_index]
    for shared_index, new_index in enumerate(shared_new_positions):
        new_is_inserted[new_index] = shared_new_is_inserted[shared_index]
    return old_is_deleted, new_is_inserted


def walk_script(old_is_deleted, new_is_inserted):
    """Yield ("keep", old_index, new_index) and
    ("change", delete_start, delete_end, insert_start, insert_end) blocks.

    A change block holds all consecutive deletions followed by all
    insertions, which gives the delete-first output order.
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

        delete_start = old_index
        insert_start = new_index
        while old_index < len(old_is_deleted) and old_is_deleted[old_index]:
            old_index += 1
        while new_index < len(new_is_inserted) and new_is_inserted[new_index]:
            new_index += 1
        yield ("change", delete_start, old_index, insert_start, new_index)


def format_ranges(is_marked):
    """Format marked positions as "3-7,9-10" (end exclusive), or "." if none."""
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
    """Build the "? old_ranges | new_ranges" line by diffing the characters."""
    old_text = old_line.decode("utf-8", "surrogateescape")
    new_text = new_line.decode("utf-8", "surrogateescape")
    old_char_is_deleted, new_char_is_inserted = find_edits(old_text, new_text)
    highlight_text = "? %s | %s\n" % (format_ranges(old_char_is_deleted),
                                      format_ranges(new_char_is_inserted))
    return highlight_text.encode("utf-8", "surrogateescape")


def run_diff(mode, old_path, new_path):
    """Print the diff and return the exit code."""
    try:
        old_lines = read_lines(old_path)
        new_lines = read_lines(new_path)
    except OSError as error:
        sys.stderr.write("error: %s\n" % error)
        return 2

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
            # The n-th inserted line pairs with the n-th deleted line.
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
