import os

from data_analysis.data_tools.flux_query_builder import FluxQuery
from data_analysis.data_tools.time_series import TimeSeries
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import math

load_dotenv()

INFLUX_URL = "http://influxdb.telemetry.ubcsolar.com"
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG")


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

    def query_time_series(self, start: str, stop: str, field: str, bucket: str = "CAN_log", car: str = "Brightside", granularity: float = 0.1, units: str = "", measurement: str = None) -> TimeSeries:
        """
        Query the database for a specific field, over a certain time range.
        The data will be processed into a TimeSeries, which has homogenous and evenly-spaced (temporally) elements.
        Data will be re-interpolated to have temporal granularity of ``granularity``.

        :param start: the start time of the query as an ISO 8601-compliant string, such as "2024-06-30T23:00:00Z".
        :param stop: the end time of the query as an ISO 8601-compliant string, such as "2024-06-30T23:00:00Z".
        :param field: the field which is to be queried.
        :param str bucket: the bucket which will be queried
        :param car: the car which data is being queried for, default is "Brightside".
        :param granularity: the temporal granularity of the resulting TimeSeries in seconds, default is 0.1s.
        :param units: the units of the returned data, optional.
        :return: a TimeSeries of the resulting time-series data
        """
        # Make the query
        query = FluxQuery().from_bucket("CAN_log").range(start=start, stop=stop).filter(field=field).car(car)
        if measurement:
            query = query.filter(measurement=measurement)
        query_df = self.query_dataframe(query)

        if isinstance(query_df, list):
            raise ValueError("Query returned multiple fields! Please refine your query.")

        if len(query_df) == 0:
            raise ValueError("Query is empty! Verify that the data is visible on InfluxDB for the queried bucket.")

        # Transform the DataFrame into a nicer format where we have our time-series data indexed by time
        query_df['_time'] = pd.to_datetime(query_df['_time'])
        query_df.set_index('_time', inplace=True)

        # Get the x-axis in relative seconds (first element is t=0)
        x_axis = query_df.index.map(lambda x: x.timestamp()).to_numpy()
        x_axis -= x_axis[0]  # Subtract off first time, so the x_axis starts at 0 with units of seconds

        # Reshape the x-axis to have the right number of elements for our needed granularity
        temporal_length: float = x_axis[-1]  # Total time of the query in seconds
        desired_num_elements: int = math.ceil(temporal_length / granularity)
        desired_x_axis = np.linspace(0, temporal_length, desired_num_elements, endpoint=True)

        # Re-interpolate our data on desired x-axis
        wave = query_df[[field]].to_numpy().reshape(-1)
        wave_interpolated = np.interp(desired_x_axis, x_axis, wave)

        actual_granularity = np.mean(np.diff(desired_x_axis))

        # Compile metadata
        meta: dict = {
            "start": query_df.index.to_numpy()[0].to_pydatetime(),
            "stop": query_df.index.to_numpy()[-1].to_pydatetime(),
            "car": query_df["car"][0],
            "measurement": query_df["_measurement"][0],
            "field": field,
            "granularity": actual_granularity,
            "length": temporal_length,
            "units": units,
        }

        new_wave = TimeSeries(wave_interpolated, meta)

        return new_wave


if __name__ == "__main__":
    start = "2024-07-07T02:23:57Z"
    stop = "2024-07-07T02:34:15Z"
    client = InfluxClient()

    pack_voltage: TimeSeries = client.query_time_series(start, stop, "MotorCurrent", units="V", measurement="MCB")
    pack_current: TimeSeries = client.query_time_series(start, stop, "PackCurrent", units="A")
    vehicle_velocity: TimeSeries = client.query_time_series(start, stop, "VehicleVelocity", units="m/s")
    pack_current, pack_voltage = TimeSeries.align(pack_current, pack_voltage)


