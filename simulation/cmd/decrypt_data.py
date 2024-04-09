"""
Decrypt all files that are expected to be in VCS as encrypted bytes.
Requires the encryption key to be in the user's .env.
"""

import os
from simulation.cache.weather import weather_directory
from pathlib import Path
from simulation.utils import Decryptor, Key
from dotenv import load_dotenv


load_dotenv()


def decrypt(decryptor: Decryptor, src: Path, dest: Path) -> None:
    """
    Decrypt the data in ``src`` using ``decryptor`` and write it to ``dest``.
    :param decryptor: Decryptor to perform the decryption
    :param src: Source file to be decrypted
    :param dest: Destination file for decrypted data, will be overwritten
    """

    with open(src, 'rb') as file:
        encrypted_data: bytes = file.read()

    decrypted_data: bytes = decryptor.decrypt(encrypted_data)

    with open(dest, 'wb') as file:
        file.write(decrypted_data)


if __name__ == "__main__":
    key_str = os.getenv("ENCRYPTION_KEY")
    decryptor = Decryptor(Key.from_str(key_str))

    decrypt(decryptor, weather_directory / 'weather_data_FSGP_SOLCAST.bin', weather_directory / 'weather_data_FSGP_SOLCAST.npz' )
