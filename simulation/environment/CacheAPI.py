import argparse
from dotenv import load_dotenv


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("race", help="Race Acronym ['FSGP', 'ASC']")
    args = parser.parse_args()

    print(f"Race Acronym: {args.race}")
