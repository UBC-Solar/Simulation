import argparse
from dotenv import load_dotenv
from simulation.utils import Query

# load API keys from environment variables
load_dotenv()


# ------------------- Script -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", help="Race Acronym ['FSGP', 'ASC']")
    parser.add_argument("--api", help="API(s) to cache ['GIS', 'WEATHER', 'ALL']")
    parser.add_argument("--weather_provider", help="Weather Provider ['SOLCAST', 'OPENWEATHER]", default='SOLCAST',
                        required=False)
    args = parser.parse_args()

    query: Query = Query(args.api, args.race, args.weather_provider)
    query.make()
