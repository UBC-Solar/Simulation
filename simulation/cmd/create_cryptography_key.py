"""
This script generates a new cryptography key and appends it to the user's .env file.
Requires a .env file in ``Simulation/simulation/cmd`` (where it should be located!).
"""
from simulation.utils.Cryptographer import Key
import os


if __name__ == "__main__":
    key = Key.new().to_str()

    try:
        with open(os.path.join(os.getcwd(), "simulation", "cmd", ".env"), 'a') as file:
            file.write(f"ENCRYPTION_KEY={key}")

    except FileNotFoundError:
        print("Couldn't find .env! Ensure to run from Simulation root directory "
              "and that a '.env' exists in Simulation/simulation/cmd.")
