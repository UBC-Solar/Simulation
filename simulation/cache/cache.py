import numpy as np
import os
from pathlib import Path
from pickle import UnpicklingError
from typing import Dict, Union, TypeAlias

HashLike: TypeAlias = Union[str, list, np.ndarray, int]


def _hash_equality(hash_1: HashLike, hash_2: HashLike) -> bool:
    return str(hash_1) == str(hash_2)


def query_npz_from_cache(cache_dir: str, filename: str, expected_hash: str = None, match_hash: bool = True) -> Dict[str, np.ndarray]:
    """
    Query a NumPy Archive (.npz) from the cache, looking in ``cache_dir`` for ``filename``.
    Optionally, enable ``match_hash`` to compare ``expected_hash`` with the cached hash.

    :param str cache_dir: the cache directory to be queried
    :param str filename: the cached filename, should not include file extension ".npz".
    :param str expected_hash: the hash that will be matched with the cached hash to confirm data validity if ``match_hash``
    :param bool match_hash: flag whether the expected hash should be compared with the cached hash
    :raises FileNotFoundError: if ``cache_dir`` doesn't exist, or ``filename`` doesn't exist within ``cache_dir``.
    :raises OSError: if the cache could not be loaded, indicating possible corruption
    :raises ValueError: if ``match_hash``, and the hashes do not match.
    :return: the cached data, as a dictionary of keys to ndarray.
    """
    abs_dir = (Path(__file__).parent / cache_dir).absolute()
    if not os.path.isdir(abs_dir):
        raise FileNotFoundError(f"Cache does not contain directory: {cache_dir}!")

    filepath = abs_dir / (filename + ".npz")

    if os.path.isfile(filepath):
        try:
            with np.load(str(filepath), allow_pickle=True) as cached_data:
                if match_hash:
                    if not _hash_equality(cached_data['hash'], expected_hash):
                        raise ValueError(f"Cached hash does not match expected value! \n "
                                         f"Expected: {expected_hash} \n "
                                         f"Got: {cached_data['hash']}")

                # We need to recompose the data as a dict as cached_data cannot be returned - it is a view to
                # memory that will get dropped once the context manager exits and the data becomes invalid
                data = {key: cached_data[key] for key in cached_data.files}
                return data

        except (OSError, EOFError, UnpicklingError) as e:
            raise OSError(f"Could not load {cache_dir}:{filename} from cache! Possible cache corruption. \n") from e

    else:
        raise FileNotFoundError(f"Cache directory {cache_dir} does not contain file: {filename}!")


def store_npz_to_cache(cache_dir: str, filename: str, data: Dict[str, np.ndarray], hash: str):
    """
    Store ``data`` as ``filename`` in ``cache_dir``. Attach an ``expected_hash`` that can be used to ensure
    data validity.

    :param str cache_dir: the cache directory for the data to be stored
    :param str filename: the filename for the cache, should not include file extension ".npz".
    :param str hash: the hash that will be stored with the data
    :param Dict[str, np.ndarray] data: dictionary of array names to the ``ndarray`` data.
    :return:
    """
    abs_dir = (Path(__file__).parent / cache_dir).absolute()
    os.makedirs(abs_dir, exist_ok=True)

    filepath = abs_dir / (filename + ".npz")

    np.savez(str(filepath), hash=hash, **data)
