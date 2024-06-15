"""

Parse data downloaded from InfluxDB as CSV files into numpy arrays

"""

import os
import pandas as pd
import numpy as np

DEFAULT_COLS = [
    "table",
    "_start",
    "_stop",
    "_time",
    "_value",
    "_field",
    "_measurement",
    "car",
    "class",
]


class InfluxData:
    def __init__(self, relative_filepath: str, cols=None):
        if cols is None:
            cols = DEFAULT_COLS
        self.filepath = os.path.join(os.path.dirname(__file__), relative_filepath)
        self.full_dataframe = pd.read_csv(self.filepath)
        self.dataframe = pd.read_csv(self.filepath, header=3)[cols]
        self.tables = self.split_tables()
        self.columns = self.get_columns()

    def split_tables(self):
        table_list = []
        tables = self.dataframe['table']
        for i in tables.unique():
            table = self.dataframe.loc[tables == i]
            table_list.append(table)
        return table_list

    def get_columns(self):
        columns = {}
        for table in self.tables:
            fields = table['_field'].unique()
            assert len(fields) == 1, "more than one field type in table"
            tuple_arr = np.stack((pd.to_datetime(table['_time']), table['_value']), axis=1)
            columns.update({fields[0]: tuple_arr})
        return columns


if __name__ == "__main__":
    data = InfluxData("IMU_Accel_Random.csv")
    from matplotlib import pyplot as plt

    a_x = data.columns['Acceleration_X']
    a_y = data.columns['Acceleration_Y']
    a_z = data.columns['Acceleration_Z']

    plt.scatter(a_x[:, 0], a_x[:, 1], label="x acceleration")
    plt.scatter(a_y[:, 0], a_y[:, 1], label="y acceleration")
    plt.scatter(a_z[:, 0], a_z[:, 1], label="z acceleration")

    plt.legend(loc='best')
    plt.show()
