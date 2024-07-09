import os

from data_analysis.data_tools import FluxQuery, Wave
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import math

load_dotenv()

INFLUX_URL = "http://influxdb.telemetry.ubcsolar.com"
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG")
INFLUX_BUCKET = "CAN_log"


class InfluxClient:
    """
    This class encapsulates a connection to an InfluxDB database.
    """
    def __init__(self):
        self._client = InfluxDBClient(url=INFLUX_URL, org=INFLUX_ORG, token=INFLUX_TOKEN)

    def query_dataframe(self, query: FluxQuery) -> pd.DataFrame:
        """
        Submit a Flux query, and return the result as a DataFrame.

        :param FluxQuery query: the query which will be submitted
        :return: the resulting data as a DataFrame
        """
        compiled_query = query.compile_query()
        compiled_query += ' |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value") '

        return self._client.query_api().query_data_frame(compiled_query)

    def query_time_series_wave(self, start: str, stop: str, field: str, car: str = "Brightside", granularity: float = 0.1, units: str = "") -> Wave:
        """
        Query the database for a specific field, over a certain time range.
        The data will be processed into a Wave, which has homogenous and evenly-spaced (temporally) elements.
        Data will be re-interpolated to have temporal granularity of ``granularity``.

        :param start: the start time of the query as an ISO 8601-compliant string, such as "2024-06-30T23:00:00Z".
        :param stop: the end time of the query as an ISO 8601-compliant string, such as "2024-06-30T23:00:00Z".
        :param field: the field which is to be queried.
        :param car: the car which data is being queried for, default is "Brightside".
        :param granularity: the temporal granularity of the resulting Wave in seconds, default is 0.1s.
        :param units: the units of the returned data, optional.
        :return: a Wave of the resulting time-series data
        """
        # Make the query
        query = FluxQuery().from_bucket("CAN_prod").range(start=start, stop=stop).filter(field=field).car(car)
        query_df = self.query_dataframe(query)

        # Transform the DataFrame into a nicer format where we have our time-series data indexed by time
        query_df['_time'] = pd.to_datetime(query_df['_time'])
        query_df.set_index('_time', inplace=True)

        # Get the x-axis in relative seconds (first element is t=0)
        x_axis = query_df.index.map(lambda x: x.timestamp()).to_numpy()
        x_axis -= x_axis[0]  # Subtract off first time, so the x_axis starts at 0 with units of seconds

        # Reshape the x-axis to have the right number of elements for our needed granularity
        temporal_length: float = x_axis[-1]  # Total time of the query in seconds
        desired_num_elements: int = math.ceil(temporal_length / granularity)
        desired_x_axis = np.linspace(0, temporal_length, desired_num_elements)

        # Re-interpolate our data on desired x-axis
        wave = query_df[[field]].to_numpy().reshape(-1)
        wave_interpolated = np.interp(desired_x_axis, x_axis, wave)

        # Compile metadata
        meta: dict = {
            "start": start,
            "stop": stop,
            "car": query_df["car"][0],
            "measurement": query_df["_measurement"][0],
            "field": field,
            "granularity": granularity,
            "length": temporal_length,
            "units": units,
        }

        new_wave = Wave(wave_interpolated, meta)

        return new_wave


if __name__ == "__main__":
    client = InfluxClient()
    current = client.query_time_series_wave(start="2024-06-30T22:46:30Z", stop="2024-06-30T22:50:30Z", field="PackCurrent", units="A")
    current.plot()
