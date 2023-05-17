class SimulationState:
    """

    Contains information about the state of the simulation at a time.

    """
    def __init__(self, args):

        self.origin_coord = args["origin_coord"]
        self.dest_coord = args["dest_coord"]
        self.current_coord = args["current_coord"]
        self.waypoints = args["waypoints"]

        self.start_hour = args["start_hour"]

        self.initial_battery_charge = args["initial_battery_charge"]

        self.gis_force_update = args["gis_force_update"]
        self.weather_force_update = args["weather_force_update"]
