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

        return TimeSeries.from_query_dataframe(query_df, granularity, field, units)


if __name__ == "__main__":
    start = "2024-07-07T02:23:57Z"
    stop = "2024-07-07T02:34:15Z"
    client = InfluxClient()

    pack_voltage: TimeSeries = client.query_time_series(start, stop, "MotorCurrent", units="V", measurement="MCB")
    pack_current: TimeSeries = client.query_time_series(start, stop, "PackCurrent", units="A")
    vehicle_velocity: TimeSeries = client.query_time_series(start, stop, "VehicleVelocity", units="m/s")
    pack_current, pack_voltage = TimeSeries.align(pack_current, pack_voltage)


