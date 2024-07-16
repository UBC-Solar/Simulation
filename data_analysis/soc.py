from simulation.common import BrightSide
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from numba import jit
import numpy as np


# Points extracted from datasheet in ``data_analysis/data/battery_cell_datasheet.png`` using ``plot_points.ipynb``.
points_10A = [[2.9648439643035234, 4.1750802121793535], [8.101266618510486, 4.032753978362866],
              [13.23768927271745, 3.896897118810765], [13.23768927271745, 3.793387130580592],
              [28.64695723533834, 3.702815890879191], [85.14760643161493, 3.6575302710284903],
              [198.14890482416848, 3.6510608967641045], [311.15020321672205, 3.638122148235333],
              [434.42434691768915, 3.6251833997065614], [557.6984906186566, 3.605775276913404],
              [665.5633663570032, 3.5798977798558607], [768.2918194411428, 3.547550908533932],
              [922.3844990673521, 3.502265288683231], [1081.6136013477683, 3.4569796688325307],
              [1225.4334356655636, 3.418163423246216], [1369.2532699833587, 3.379347177659901],
              [1502.8002589927403, 3.3340615578092008], [1641.4836706563285, 3.2952453122228857],
              [1795.5763502825373, 3.24505515695790277], [1954.8054525629536, 3.2046740725214846],
              [2119.170977497577, 3.1529190784063985], [2293.8093477406137, 3.1141028328200835],
              [2442.765604712616, 3.075286587233769], [2617.4039749556537, 3.0170622188542966],
              [2756.087386619243, 2.971776599003596], [2899.907220937038, 2.913552230624124],
              [3012.9085193295914, 2.84238911371588], [3100.227704451109, 2.777695371072022],
              [3182.4104669184217, 2.700062879899393], [3254.3203840773185, 2.615961014462377],
              [3300.5481879651816, 2.5447978975541337], [3326.2303012362167, 2.4995122777034333]]

points_2A = [[5.169867060561383, 4.1688311688311686], [15.509601181683795, 4.051948051948052],
             [77.54800590841933, 4.0], [144.75627769571625, 3.9935064935064934],
             [242.9837518463811, 3.9805194805194803], [398.0797636632201, 3.9415584415584415],
             [532.4963072378139, 3.909090909090909], [677.2525849335302, 3.8636363636363633],
             [811.669128508124, 3.831168831168831], [956.4254062038405, 3.779220779220779],
             [1090.8419497784344, 3.7532467532467533], [1261.4475627769566, 3.7012987012987013],
             [1432.0531757754798, 3.662337662337662], [1581.9793205317574, 3.6103896103896105],
             [1731.9054652880352, 3.571428571428571], [1881.8316100443128, 3.5259740259740258],
             [2011.0782865583458, 3.4935064935064934], [2140.3249630723776, 3.4675324675324672],
             [2269.5716395864106, 3.428571428571428], [2403.9881831610046, 3.409090909090909],
             [2548.744460856721, 3.37012987012987], [2698.6706056129988, 3.331168831168831],
             [2817.5775480059087, 3.2857142857142856], [2936.484490398818, 3.233766233766233],
             [3039.881831610044, 3.1363636363636362], [3127.769571639586, 3.0129870129870127],
             [3194.977843426883, 2.9155844155844157], [3246.676514032496, 2.7987012987012987],
             [3282.865583456425, 2.701298701298701], [3319.0546528803548, 2.5974025974025974],
             [3344.9039881831613, 2.5129870129870127]]


# Brightside Helpers


num_modules = BrightSide.num_modules
num_cells = BrightSide.num_cells_per_module * num_modules
cell_rating = BrightSide.cell_charge_rating
nominal_capacity = cell_rating * num_cells
min_voltage = BrightSide.min_voltage


# Voltage Interpolation Estimation


def interpolate_soc(voltage, interp_10A, interp_2A, current):
    ref_currents = [10, 2]
    current = np.clip(current, a_min=ref_currents[1], a_max=ref_currents[0])

    soc_10A_values = interp_10A(voltage)
    soc_2A_values = interp_2A(voltage)

    soc = soc_2A_values + (soc_10A_values - soc_2A_values) * (current - ref_currents[1]) / (
            ref_currents[0] - ref_currents[1])
    return soc


def discharge_capacity_curve_from_cell_voltage_at_10A(cell_voltage):
    params_10A = [3.80692776e+03, 3.05358486e+00, 5.65913073e+00, 1.03077310e+03,
                  -2.06935980e+02, -8.76056553e-01, 2.60572753e+00]

    return params_10A[0] / np.power(1 + np.exp(params_10A[1] * (cell_voltage - params_10A[2])), params_10A[3]) \
        + params_10A[4] * np.exp(params_10A[5] * (cell_voltage - params_10A[6]))


def discharge_capacity_curve_from_cell_voltage_at_2A(cell_voltage):
    params_2A = [-1.02680518e+01, 2.43805760e+01, -2.78558014e+00, 1.77778078e+01,
                 -2.70378393e+01, 3.08895269e+00, 2.80390256e-02, -3.75040186e-01,
                 1.56319745e+00, -1.98899865e-01, -1.49624032e+01, 3.68516384e+01,
                 -2.62416076e+01]

    return np.exp(params_2A[0] * cell_voltage + params_2A[1]) * np.polyval(params_2A[2:], cell_voltage) / np.power(
        np.polyval(params_2A[6:], cell_voltage), params_2A[5])


def discharged_capacity_from_cell_voltage(cell_voltage, current):
    interp_10A = interp1d(cell_voltage, discharge_capacity_curve_from_cell_voltage_at_10A(cell_voltage), kind='linear',
                          fill_value="extrapolate")
    interp_2A = interp1d(cell_voltage, discharge_capacity_curve_from_cell_voltage_at_2A(cell_voltage), kind='linear',
                         fill_value="extrapolate")

    return interpolate_soc(cell_voltage, interp_10A, interp_2A, current)


def get_soc_from_voltage(voltage, current):
    cell_voltage = voltage / BrightSide.num_modules  # V
    discharged_capacity = discharged_capacity_from_cell_voltage(cell_voltage, current) * num_cells  # mAh
    soc = (nominal_capacity - discharged_capacity) / nominal_capacity

    return soc


def voltage_interpolation():
    # Demonstrate voltage interpolation
    voltage = np.linspace(2.5, 4.2, 1000) * BrightSide.num_modules

    plt.plot(voltage, get_soc_from_voltage(voltage, 2), label="2A")
    plt.plot(voltage, get_soc_from_voltage(voltage, 6), label="6A")
    plt.plot(voltage, get_soc_from_voltage(voltage, 10), label="10A")

    plt.xlabel("Pack Voltage (V)")
    plt.ylabel("SoC")
    plt.title("SoC interpreted from pack voltage during discharge")

    plt.legend()
    plt.show()


# Enhanced Coulomb Counting
# https://www.analog.com/en/resources/technical-articles/a-closer-look-at-state-of-charge-and-state-health-estimation-tech.html


@jit(nopython=True)
def delta_dod(current, time):
    return -current * time / (nominal_capacity * 3.6)


@jit(nopython=True)
def get_soc_from_coulomb_counting(initial_soc: float, battery_voltage, battery_current, tick, charge_efficiency: float = 1.0, discharge_efficiency: float = 1.0):
    # Initialization
    soc = np.empty_like(battery_voltage)
    soh = np.empty_like(battery_voltage)
    dod = np.empty_like(battery_voltage)

    # Initial Conditions
    soc[0] = initial_soc
    soh[0] = 1.0
    dod[0] = 1.0 - soc[0]

    # Apply enhanced Coulomb counting algorithm
    for i, (V, I) in enumerate(zip(battery_voltage, battery_current)):
        t = i + 1                       # t := current index, i := previous index
        if t == len(battery_current):
            continue

        if I > 0:                       # Charging
            if soc[i] >= 1.0:           # Battery is full
                soh[t] = soc[i] = 1.0
                dod[t] = dod[i]

            else:                       # Battery is not full (can charge)
                soh[t] = soh[i]
                dod[t] = dod[i] + charge_efficiency * delta_dod(I, tick)
                soc[t] = soh[t] - dod[t]

        else:                           # Discharging
            if V < min_voltage:         # Empty battery
                soh[t] = dod[t] = dod[i]
                soc[t] = soc[i]

            else:                       # Battery is not empty (can discharge)
                soh[t] = soh[i]
                dod[t] = dod[i] + discharge_efficiency * delta_dod(I, tick)
                soc[t] = soh[t] - dod[t]

    return soc, soh, dod


def coulomb_counting():
    tick = 1.0
    voltage = np.full([1000], fill_value=100.)
    time = np.linspace(0, 1000, 1000)
    current = np.array([-80.] * 200 + [40.] * 300 + [-20.] * 200 + [-100.] * 100 + [30.] * 200) * 4

    soc, soh, dod = get_soc_from_coulomb_counting(0.99, voltage, current, tick)

    fig, ax = plt.subplots()
    ax.plot(time, soc, label="SOC")
    ax.plot(time, soh, label="SOH")
    ax.plot(time, dod, label="DOD")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    coulomb_counting()
