from solcast import forecast, historic
from dotenv import load_dotenv
from solcast.unmetered_locations import UNMETERED_LOCATIONS
import pandas as pd
sydney = UNMETERED_LOCATIONS['Sydney Opera House']


load_dotenv()


def main():
    # Datetime, duration, and time formats follow: ISO 8601: see https://en.wikipedia.org/wiki/ISO_8601
    hours: int = 48  # How many hours of forecast do we want
    period: str = 'PT30M'  # Granularity of forecast, see https://en.wikipedia.org/wiki/ISO_8601#Durations

    res = forecast.radiation_and_weather(
        latitude=sydney['latitude'],
        longitude=sydney['longitude'],
        hours=hours,
        period=period,
        output_parameters=[
            'ghi', 'wind_speed_10m', 'wind_direction_10m'
        ],  # see https://docs.solcast.com.au/#9de907e7-a52f-4993-a0f0-5cffee78ad10
    ).to_pandas()

    print(res)


if __name__ == '__main__':
    main()
