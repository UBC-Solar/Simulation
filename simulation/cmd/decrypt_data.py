"""
Decrypt all files that are expected to be in VCS as encrypted bytes.
Requires the encryption key to be in the user's .env.
"""

import os
from simulation.cache.weather import weather_directory
from simulation.utils import Decryptor, Key
from dotenv import load_dotenv


load_dotenv()


if __name__ == "__main__":
    key_str = os.getenv("ENCRYPTION_KEY")
    decryptor = Decryptor(Key.from_str(key_str))

    with open(weather_directory / 'weather_data_FSGP_SOLCAST.bin', 'rb') as file:
        encrypted_data: bytes = file.read()

    decrypted_data: bytes = decryptor.decrypt(encrypted_data)
    print(decrypted_data)
    with open(weather_directory / 'weather_data_FSGP_SOLCAST.npz', 'wb') as file:
        file.write(decrypted_data)
