class SimulationState:
    def __init__(self, args):

        self.origin_coord = args["origin_coord"]
        self.dest_coord = args["dest_coord"]
        self.waypoints = args["waypoints"]

        self.start_hour = args["start_hour"]

        self.initial_battery_charge = args["initial_battery_charge"]

        self.gis_force_update = args["gis_force_update"]
        self.weather_force_update = args["weather_force_update"]