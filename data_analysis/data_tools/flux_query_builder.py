"""
ORM-like query-building tools for Flux, InfluxDB's querying language
"""
from typing import Callable, List
from dateutil import parser


# Function signature required for a Flux statement formatter
FluxFormatter = Callable[[List[str]], str]


class FluxStatement:
    """
    This class encapsulates a single Flux query statement, such as "filter(fn:(r) => r._field == "TotalPackVoltage").
    """
    def __init__(self, statement: str, priority: int):
        assert isinstance(statement, str), f"Statement must be of type `str`, not {type(statement)}!"
        assert (isinstance(priority, int) and priority >= 0), f"Priority must be a non-negative integer!"

        self._statement: str = statement
        self._priority: int = priority

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def statement(self) -> str:
        return self._statement


class FluxStatementTemplate:
    def __init__(self, formatter: FluxFormatter, priority: int):
        assert isinstance(formatter, Callable), f"formatter must have signature `Callable[[List[str]], str]`!"
        assert (isinstance(priority, int) and priority >= 0), f"Priority must be a non-negative integer!"

        self._formatter: FluxFormatter = formatter
        self._priority: int = priority

    def get(self, items: List[str]) -> FluxStatement:
        return FluxStatement(self._formatter(items), self.priority)

    @property
    def priority(self) -> int:
        return self._priority


class FluxQuery:
    # Static instantiations of valid Flux statements
    _from_bucket_formatter: FluxFormatter = lambda args: f'from(bucket: "{args[0]}") '
    _from_bucket_statement = FluxStatementTemplate(formatter=_from_bucket_formatter, priority=0)

    _unbound_range_formatter: FluxFormatter = lambda args: f'range(start: {args[0]}) '
    _unbound_range_statement = FluxStatementTemplate(formatter=_unbound_range_formatter, priority=1)

    _bound_range_formatter: FluxFormatter = lambda args: f'range(start: {args[0]}, stop: {args[1]}) '
    _bound_range_statement = FluxStatementTemplate(formatter=_bound_range_formatter, priority=1)

    _filter_measurement_formatter: FluxFormatter = lambda args: f'filter(fn:(r) => r._measurement == "{args[0]}") '
    _filter_measurement_statement = FluxStatementTemplate(formatter=_filter_measurement_formatter, priority=2)

    _filter_field_formatter: FluxFormatter = lambda args: f'filter(fn:(r) => r._field == "{args[0]}") '
    _filter_field_statement = FluxStatementTemplate(formatter=_filter_field_formatter, priority=3)

    _car_formatter: FluxFormatter = lambda args: f'filter(fn:(r) => r.car == "{args[0]}") '
    _car_statement = FluxStatementTemplate(formatter=_car_formatter, priority=3)

    def __init__(self):
        self._statements: List[FluxStatement] = []

    def from_bucket(self, bucket: str):
        """
        Specify the bucket that will be queried from.

        :param str bucket: bucket name
        """
        assert isinstance(bucket, str), f"Bucket must be a `str`, not {type(bucket)}!"

        new_statement = FluxQuery._from_bucket_statement.get([bucket])
        self._statements.append(new_statement)

        return self

    def range(self, start: str, stop: str = None):
        """
        Specify the time range of the time-series data to query.

        :param start: start time of the time range as an ISO 8601 compliant string.
        :param stop: stop time of the time range as an ISO 8601 compliant string, optional.
        """
        # Verify that `start` and `stop` are valid ISO 8601 dates.
        try:
            parser.parse(start)
            if stop is not None:
                parser.parse(stop)
        except parser.ParserError:
            raise ValueError("Invalid dates provided to range! Must be of ISO 8601 format.")

        if stop is not None:
            new_statement = FluxQuery._bound_range_statement.get([start, stop])
            self._statements.append(new_statement)

        else:
            new_statement = FluxQuery._unbound_range_statement.get([start])
            self._statements.append(new_statement)

        return self

    def filter(self, measurement: str = None, field: str = None):
        """
        Apply a filter to the query. Any or both of ``measurement`` and ``field`` may be specified and both filters will
        be applied. No effect if neither is.

        :param measurement: measurement to filter for, such as "BMS"
        :param field: field to filter for, such as "PackCurrent".
        """
        if measurement is not None:
            new_statement = FluxQuery._filter_measurement_statement.get([measurement])
            self._statements.append(new_statement)

        if field is not None:
            new_statement = FluxQuery._filter_field_statement.get([field])
            self._statements.append(new_statement)

        return self

    def car(self, car: str):
        """
        Filter for data from a specific car.

        :param car: car name, such as "Brightside".
        :return:
        """
        assert isinstance(car, str), f"Car must be a `str`, not {type(car)}!"

        new_statement = FluxQuery._car_statement.get([car])
        self._statements.append(new_statement)

        return self

    def inject_raw(self, statement: FluxStatement):
        """
        Inject a FluxStatement into this query. This may be necessary if the
        Flux statement is not available with the existing API.

        :param statement:
        :return:
        """
        self._statements.append(statement)

        return self

    def compile_query(self) -> str:
        """
        Compile this object into a Flux query, as a string.
        """
        sorted_statements = sorted(self._statements, key=lambda statement: statement.priority)

        compiled_statement = sorted_statements.pop(0).statement
        for flux_statement in sorted_statements:
            compiled_statement += f"|> {flux_statement.statement}"

        return compiled_statement
