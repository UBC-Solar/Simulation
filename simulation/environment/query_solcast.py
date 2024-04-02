from solcast import forecast, historic
from dotenv import load_dotenv
from solcast.unmetered_locations import UNMETERED_LOCATIONS
import pandas as pd
sydney = UNMETERED_LOCATIONS['Sydney Opera House']


load_dotenv()


def main():
    res = historic.radiation_and_weather(
        latitude=sydney['latitude'],
        longitude=sydney['longitude'],
        start='2022-06-01T06:00',
        end='2022-06-02T06:00',
        # duration='P1D',  # see https://en.wikipedia.org/wiki/ISO_8601#Durations
        output_parameters='ghi,wind_speed_10m,wind_direction_10m',  # see https://docs.solcast.com.au/#9de907e7-a52f-4993-a0f0-5cffee78ad10
    ).to_pandas()

    print(res)


if __name__ == '__main__':
    main()
