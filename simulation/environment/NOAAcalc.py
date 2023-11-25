eg_latitude = 30
eg_longitude = 30
eg_excel_date = 40350.00  # days since 1900
eg_local_time_past_midnight = 0.5  # in days (e.g. 12pm is 0.5)
eg_time_zone = -6


def julian_day(excel_date, local_time_past_midnight, time_zone):
    return excel_date+2415018.5+local_time_past_midnight-time_zone/24

