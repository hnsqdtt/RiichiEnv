def tid_to_mpsz(tid: int) -> str:
    """
    Convert 136-based tile ID to MPSZ string (e.g. 1z, 5p, 0p).
    0-based index: 0 is red 5 for m, p, s.
    """
    if not (0 <= tid < 136):
        raise ValueError(f"Invalid TID: {tid}")

    # Check Red 5
    # 5m: 16-19. 16 is red (usually).
    # 5p: 52-55. 52 is red.
    # 5s: 88-91. 88 is red.
    if tid == 16:
        return "0m"
    if tid == 52:
        return "0p"
    if tid == 88:
        return "0s"

    kind = tid // 36
    if kind < 3:
        suit_char = ["m", "p", "s"][kind]
        offset = tid % 36
        num = offset // 4 + 1
        return f"{num}{suit_char}"
    else:
        offset = tid - 108
        num = offset // 4 + 1
        return f"{num}z"


def tid_to_mjai(tid: int) -> str:
    """
    Convert 136-based tile ID to MJAI string (e.g. E, 5p, 5pr).
    """
    if not (0 <= tid < 136):
        raise ValueError(f"Invalid TID: {tid}")

    # Red 5s
    if tid == 16:
        return "5mr"
    if tid == 52:
        return "5pr"
    if tid == 88:
        return "5sr"

    kind = tid // 36
    if kind < 3:
        suit_char = ["m", "p", "s"][kind]
        offset = tid % 36
        num = offset // 4 + 1
        return f"{num}{suit_char}"
    else:
        offset = tid - 108
        num = offset // 4 + 1
        # MJAI Honors: E, S, W, N, P, F, C
        mjai_honors = ["E", "S", "W", "N", "P", "F", "C"]
        if 1 <= num <= 7:
            return mjai_honors[num - 1]
        return f"{num}z"  # Fallback? Should not reach


def mpsz_to_tid(mpsz_str: str) -> int:
    """
    Convert MPSZ string to TID. Returns canonical TID.
    e.g. 1z -> 108, 0p -> 52, 5p -> 53 (non-red).
    """
    if not mpsz_str:
        raise ValueError("Empty string")

    suit = mpsz_str[-1]
    num_str = mpsz_str[:-1]

    if suit not in ["m", "p", "s", "z"]:
        raise ValueError(f"Invalid suit: {suit}")

    try:
        num = int(num_str)
    except ValueError:
        raise ValueError(f"Invalid number: {num_str}")

    if suit == "z":
        if not (1 <= num <= 7):
            raise ValueError(f"Invalid honor number: {num}")
        # 1z start 108. (num-1)*4 + 108
        return 108 + (num - 1) * 4

    # m, p, s
    suit_idx = {"m": 0, "p": 1, "s": 2}[suit]
    base_idx = 36 * suit_idx

    if num == 0:
        # Red 5
        # 5m: 16, 5p: 52 (36+16), 5s: 88 (72+16)
        return base_idx + 16

    if not (1 <= num <= 9):
        raise ValueError(f"Invalid number: {num}")

    # Normal tile
    # (num-1)*4
    offset = (num - 1) * 4
    # If 5 (non-red), we skip the red one (index 0 of the set of 4 5s) usually?
    # IDs for 5: 16,17,18,19 (relative: 16,17,18,19 of suit block 0-35)
    # Relative offset for 5 is 16.
    # 0 -> 16 (Red)
    # 5 -> 17 (Non-Red)?
    # My tid_to_mpsz: 16->0m. 17->5m.
    # So if num is 5, we should return the first non-red 5.
    # 5m: 16(R), 17, 18, 19.
    # If input is '5m', return 17.

    tid = base_idx + offset
    if num == 5:
        # Check against red ID logic.
        # offset for 5 is 16.
        # base+16 is red.
        # We want non-red, so +1?
        return base_idx + 16 + 1

    return tid


def mpsz_to_mjai(mpsz_str: str) -> str:
    # mpsz -> tid -> mjai
    tid = mpsz_to_tid(mpsz_str)
    return tid_to_mjai(tid)


def mjai_to_tid(mjai_str: str) -> int:
    """
    Convert MJAI string to TID.
    E, S, W, N, P, F, C -> Honors
    5pr -> Red 5p (52)
    5p -> Non-red 5p (53)
    """
    # Check Honors
    honors_map = {"E": 1, "S": 2, "W": 3, "N": 4, "P": 5, "F": 6, "C": 7}
    if mjai_str in honors_map:
        num = honors_map[mjai_str]
        return 108 + (num - 1) * 4

    # Check Red Suffix 'r'
    is_red = mjai_str.endswith("r")
    core = mjai_str[:-1] if is_red else mjai_str

    # Parse core as if it were mpsz, but note honor handling
    # MJAI uses 5mr.
    # Core is 5m.

    # Use mpsz_to_tid logic for core?
    # But wait, MJAI string '5p' (no r) is 5p non-red.
    # mpsz string '5p' is also 5p non-red.
    # mpsz string '0p' is 5p red.

    # If is_red is True, we want 0p equivalent.

    if is_red:
        # Expected core: 5m, 5p, 5s.
        if core not in ["5m", "5p", "5s"]:
            raise ValueError(f"Invalid red spec: {mjai_str}")
        # Convert to 0m, 0p, 0s
        mpsz_equiv = "0" + core[1:]
        return mpsz_to_tid(mpsz_equiv)

    return mpsz_to_tid(mjai_str)


def mjai_to_mpsz(mjai_str: str) -> str:
    tid = mjai_to_tid(mjai_str)
    return tid_to_mpsz(tid)


# List versions
def tid_to_mpsz_list(tid_list: list[int]) -> list[str]:
    return [tid_to_mpsz(t) for t in tid_list]


def tid_to_mjai_list(tid_list: list[int]) -> list[str]:
    return [tid_to_mjai(t) for t in tid_list]


def mpsz_to_tid_list(mpsz_list: list[str]) -> list[int]:
    """
    Convert list of mpsz strings to list of TIDs, ensuring uniqueness by tracking used counts.
    e.g. ["1m", "1m"] -> [0, 1]
    """
    tid_list = []
    tid_counts = {}

    for s in mpsz_list:
        base_tid = mpsz_to_tid(s)

        # Red Handling: mpsz_to_tid returns 16 for "0m", 17 for "5m" (if logic fixed)?
        # Let's align with single-call logic or implement robust tracker.

        # Assuming mpsz_to_tid returns the BASE ID for the requested type (or Specific Red ID).
        # We need to apply offset.

        # We need to distinguish if the base_tid implies a specific unique tile (Red) or a group.
        # 16 ("0m") is specific.
        # 17 ("5m") is start of group?

        # To be safe, we track usage per "Logical Type" or strictly per base_tid.
        # Using base_tid + count is unsafe if bases are close and collide?
        # 0 (1m) -> 0,1,2,3.
        # 4 (2m) -> 4,5,6,7.
        # Safe.

        # Red 5s:
        # "0m" -> 16.
        # "5m" -> should return 17?
        # If convert.py mpsz_to_tid logic returns 17 for 5m.
        # Then 16 is tracked separately.
        # 17 is tracked separately (17->18->19).
        # This seems safe.

        cnt = tid_counts.get(base_tid, 0)
        final_tid = base_tid + cnt

        # Sanity check: Ensure we don't overflow the type?
        # Max 4 per type.
        # If input has["1m"]*5, we produce invalid ID?
        # But log data should be valid.

        tid_list.append(final_tid)
        tid_counts[base_tid] = cnt + 1

    return tid_list


def mpsz_to_mjai_list(mpsz_list: list[str]) -> list[str]:
    return [mpsz_to_mjai(s) for s in mpsz_list]


def mjai_to_tid_list(mjai_list: list[str]) -> list[int]:
    tid_list = []
    tid_counts = {}

    for s in mjai_list:
        base_tid = mjai_to_tid(s)

        # mjai_to_tid returns canonical. Same duplicate issue.
        # Apply strict offset tracking.

        # Red tile check?
        # mjai "5mr" -> 16.
        # mjai "5m" -> 17? (If mjai_to_tid logic correct).
        # We trust base_tid separates Red/Non-Red.

        cnt = tid_counts.get(base_tid, 0)
        final_tid = base_tid + cnt

        tid_list.append(final_tid)
        tid_counts[base_tid] = cnt + 1

    return tid_list


def mjai_to_mpsz_list(mjai_list: list[str]) -> list[str]:
    return [mjai_to_mpsz(s) for s in mjai_list]


def paishan_to_wall(paishan_str: str) -> list[int]:
    """
    Parses a paishan string (concatenated MPSZ, e.g. "1m2m3p") into a list of 136 unique Tile IDs.
    Handles duplicate tiles by tracking counts (e.g. first "1m" -> 0, second "1m" -> 1).
    """
    if len(paishan_str) % 2 != 0:
        raise ValueError(f"Invalid paishan string length: {len(paishan_str)}")

    wall = []
    tid_count = {}

    for i in range(0, len(paishan_str), 2):
        chunk = paishan_str[i : i + 2]
        tid_base = mpsz_to_tid(chunk)

        # Determine offset for uniqueness (0, 1, 2, 3)
        # mpsz_to_tid returns the base canonical ID.
        # We assume paishan lists tiles sequentially.
        # If "1m" appears 4 times, they should map to canonical, canonical+1, etc.
        # EXCEPT for Red 5s?
        # mpsz_to_tid("0m") -> 16 (Red 5m).
        # mpsz_to_tid("5m") -> 17 (Normal 5m start).
        # If paishan has "0m", it maps to 16. Count 0 -> 16.
        # If paishan has "5m" x 3, it maps to 17. Count 0->17, 1->18, 2->19.
        # This assumes the canonical ID base accounts for Red/Non-Red distinction correctly.
        # 5m (17) range is 17, 18, 19? Or 16, 17, 18, 19?
        # Let's check mpsz_to_tid implementation.
        # 5m -> 17?
        # 5m Red is 16.
        # Normal 5m starts at 17? Or 16?
        # Typically 5m TIDs: 16, 17, 18, 19.
        # If 16 is Red, then 17, 18, 19 are normal.
        # mpsz_to_tid("5m"):
        #   base_idx = 0. num=5.
        #   return base_idx + (4*4) = 16? No.
        #   offset = (num-1)*4 = 16. returns 0+16 = 16.
        #   So "5m" returns 16?
        #   Wait, line 90: base_idx = 36 * suit_idx.
        #   line 103: return base_idx + (num - 1) * 4.
        #   For 5m: 0 + (4)*4 = 16.
        #   But Red 5 check at line 94: if num==0 return base_idx+16.
        #   So "0m" -> 16. "5m" -> 16.
        #   This is a collision if we use simple offsets!
        #   But TIDs are unique 0-135.
        #   5m (Red) is 16. 5m (Normal) are 17, 18, 19.
        #   If `mpsz_to_tid("5m")` returns 17, good.
        #   Let's check code.

        cnt = tid_count.get(tid_base, 0)

        # Correction for 5s:
        # If "0m" (Red) comes, it uses TID 16.
        # If "5m" comes, it uses TID ?
        # We need to ensure we don't produce duplicate TIDs.
        # If base logic returns 16 for "5m", and we have "0m" (16) and "5m" (16),
        # we need to shift "5m" to 17, 18, 19.

        # Current mpsz_to_tid logic (inferred):
        # returns base_idx + (num-1)*4. So "5m" -> 16.
        # "0m" -> 16.
        # So "5m" and "0m" collide at base 16.

        # Assign a concrete tile ID from the base ID, ensuring consistency with
        # `tid_to_mpsz`: 0m/0p/0s must map to the red IDs (16, 52, 88), and the
        # corresponding 5m/5p/5s tiles must use the remaining non-red IDs.
        real_tid = tid_base

        # Red Handling
        is_red_str = chunk.startswith("0")
        if is_red_str:
            # tid_base is correct (e.g. 16 for 0m)
            # Just use it.
            pass
        else:
            # "5m" -> 16. Since we want non-red, we start at 17?
            # Check collision with Red ID.
            # 5m base is 16.
            # If 16 is reserved for Red, normal start at 17.
            if tid_base in [16, 52, 88]:
                real_tid += 1  # Start at 17, 53, 89

        # Now apply offset for multiples
        # We track count per real_tid base?
        # No, for normals like "1m" (0): 0, 1, 2, 3.
        # "5m" (17): 17, 18, 19.
        # count for 17 should increment 17->18->19.

        cnt = tid_count.get(real_tid, 0)
        final_tid = real_tid + cnt
        tid_count[real_tid] = cnt + 1

        wall.append(final_tid)

    return wall
