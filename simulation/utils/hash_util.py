import hashlib
import json
from typing import Dict


def hash_dict(value: Dict, num_chars: int = 12) -> int:
    """
    Create a consistent hash for a dictionary by converting it to a string with sorted keys
    and then applying a SHA-256 hash.
    """
    # Convert the data to a JSON string, sorting keys to ensure consistent ordering
    serialized_data = json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)

    # Use SHA-256 for consistent and robust hashing
    return int(hashlib.sha256(serialized_data.encode('utf-8')).hexdigest()[:num_chars], 16)
