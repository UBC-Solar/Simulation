# Radius of the Earth (m)
EARTH_RADIUS = 6371009

# Acceleration caused by gravity (m/s^2)
ACCELERATION_G = 9.81

# Density of Air at 15C and 101kPa (kg/m^3)
AIR_DENSITY = 1.225

# Maximum number of waypoints that can be given to generate route data
MAX_WAYPOINTS = 10

# Solar Irradiance (W/m^2)
SOLAR_IRRADIANCE = 1353

# As we currently have a limited number of API calls(60) every minute with the
# current Weather API, we must shrink the dataset significantly. As the
# OpenWeatherAPI models have a resolution of between 2.5 - 70 km, we will
# go for a resolution of 25km. Assuming we travel at 100km/h for 12 hours,
# 1200 kilometres/25 = 48 API calls
# As the Google Maps API has a resolution of around 40m between points,
# for ASC, we must cull at 625:1 (because 25,000m / 40m = 625)
REDUCTION_FACTOR = 625
