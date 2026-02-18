"""Normalization helpers for operational reconciliation.

Every module in this repository carries detailed comments so junior engineers
immediately understand the intent of each line. This file focuses on Lot ID
cleanup which is required by AC1 (matching by Lot ID + Date).

Complexity guarantees:
- canonicalize_lot runs in O(n) time, where n is the number of characters in
  the raw lot string, because each transformation walks the string once.
- The function allocates O(n) additional space to build the normalized copy.
"""
from typing import Optional
import re

# Compile regular expressions up front so repeated calls do not pay the cost of
# recompiling patterns. This is still O(1) space/time per call after the first.
_NON_ALNUM = re.compile(r"[^A-Z0-9]")

# Canonical prefix we strip when sheets include strings such as "LOT123".
_LOT_PREFIX = "LOT"


def canonicalize_lot(lot_raw: Optional[str]) -> Optional[str]:
    """Return a canonical lot identifier for matching across sources.

    Args:
        lot_raw: Original string (possibly malformed) from spreadsheets.

    Returns:
        An uppercase alphanumeric token without the literal prefix `LOT`, or
        None when the input cannot produce a usable key.

    Notes for junior engineers:
    - Empty/None values short-circuit to keep behavior predictable.
    - Whitespace trimming and uppercasing must happen before regex cleanup to
      avoid losing meaningful characters.
    - We explicitly replace the OCR typo `L0T` (zero) with `LOT` (letter O)
      because it surfaced repeatedly in the provided spreadsheets.
    - Removing all characters that are not [A-Z0-9] prevents punctuation or
      spaces from breaking joins across tables.
    - Stripping the literal prefix `LOT` makes keys consistent whether the
      sheet used "LOT123" or just "123".
    - If the normalized token becomes empty we return None to signal that this
      source row should be counted under "Incomplete records" (AC3).

    Time complexity: O(n) because each transformation scans the string once.
    Space complexity: O(n) for the cleaned copy of the string.
    """
    # Guard clause keeps runtime O(1) when the input is already empty/None by
    # exiting early without allocating intermediate strings.
    if not lot_raw:
        return None

    # Coerce values to string before trimming so numeric lot ids (ints/floats)
    # from databases can still be canonicalized without raising AttributeError.
    s = str(lot_raw).strip().upper()

    # Fix common OCR/typing issues (L0T vs LOT) before removing non-alphanumerics.
    s = s.replace("L0T", "LOT")

    # Remove all characters that are not letters/numbers to keep the join key
    # clean (regex substitution runs in O(n)).
    s = _NON_ALNUM.sub("", s)

    # Drop the literal prefix "LOT" so both "LOT2024" and "2024" join cleanly.
    if s.startswith(_LOT_PREFIX):
        s = s[len(_LOT_PREFIX) :]

    # If nothing remains after cleaning, treat it as missing data.
    if not s:
        return None

    # Return the canonical token so callers can store it alongside the raw
    # string for traceability back to spreadsheets.
    return s
