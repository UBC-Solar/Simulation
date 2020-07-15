#!usr/bin/env python

import requests
import json
import polyline
import numpy as np


class GIS:


    def __init__(self, api_key, origin_coord, dest_coord, waypoints):

        #Radius of the Earth in metres
        self.R = 6371009

        self.api_key = api_key
       
        self.current_index = 0
        self.distance_remainder = 0 
      
        self.path = self.update_path(origin_coord, dest_coord, waypoints)

        self.path_elevations = self.calculate_path_elevations(self.path)

        self.path_distances = self.calculate_path_distances(self.path)
         
        self.path_gradients = self.calculate_path_gradients(self.path_elevations,\
                                 self.path_distances)
        

    def get_path(self):
        """
        Returns all N coordinates of the path in a numpy array 
        [N][latitude, longitude]
        """

        return self.path

    
    def get_path_elevations(self):
        """
        Returns all N elevations of the path in a numpy array
        [N][elevation]
        """

        return self.path_elevations


    def get_path_distances(self):
        """
        Returns all N-1 distances of the path in a numpy array
        [N-1][elevation]
        """

        return self.path_distances


    def get_path_gradients(self):
        """
        Returns all N-1 gradients of a path in a numpy array
        [N-1][gradient]
        """

        return self.path_gradients


    def calculate_path_elevations(self, coords):
        """
        Returns the elevations of every coordinate the array of coordinates passed in 
            as a coordinate

        coords: A numpy array [n][latitude, longitude]

        Returns: A numpy array [n][elevation] in metres
        """
        
        #construct URL
        url_head = 'https://maps.googleapis.com/maps/api/elevation/json?locations='
   
        location_strings = []
        locations = ""
        for coord in coords:
            
            locations = locations + "{},{}|".format(coord[0],coord[1])

            if len(locations) > 8000:
                location_strings.append(locations[:-1])
                locations = ""

        if len(locations) != 0:
            location_strings.append(locations[:-1])

        url_tail = "&key={}".format(self.api_key)

        #Get elevations
        elevations = np.zeros(len(coords))

        i = 0
        for location_string in location_strings:

            url = url_head + location_string + url_tail

            r = requests.get(url)
            response = json.loads(r.text)

            if response['status'] == "OK":
                
                for result in response['results']:
                
                    elevations[i] = result['elevation'] 
                    i = i + 1

            else:
                print("Error: No elevation was found")

        
        return elevations

    
    def calculate_current_elevation(self):
        """
        Get the elevation of the closest point to the current point  
        """
    
        return elevations[self.current_index]
                    
        
    def calculate_path_distances(self, coords):
        """
        The coordinates are spaced quite tightly together, and they capture the 
            features of the road. So, the lines between every pair of adjacent 
            coordinates can be treated like a straight line, and the distances can
            thus be obtained.
        
        coords: A numpy array [n][latitute, longitude]
        
        Returns:
            - A numpy array [n-1][distances],
        """
        
        offset = np.roll(coords, (1, 1))
      
        #get the latitude and longitude differences, in radians
        diff = (coords - offset)[1:] * np.pi/180
        diff_lat, diff_lng = np.split(diff, 2, axis=1)
        diff_lat = np.squeeze(diff_lat)
        diff_lng = np.squeeze(diff_lng)

        print("diff_lat: {}".format(diff_lat.shape))
        print("diff_lng: {}".format(diff_lng.shape))
        
        #get the mean latitude for every latitude, in radians
        mean_lat = ((coords + offset)[1:, 0] * np.pi/180)/ 2
        cosine_mean_lat = np.cos(mean_lat)
        
        print("cosine_mean_lat: {}".format(cosine_mean_lat.shape))
        
        #multiply the latitude difference with the cosine_mean_latitude
        diff_lng_adjusted = cosine_mean_lat * diff_lng 
        
        print("diff_lng_adjusted: {}".format(diff_lng_adjusted.shape))
        
        #square, sum and square-root
        square_lat = np.square(diff_lat)
        square_lng = np.square(diff_lng_adjusted)
        square_sum = square_lat + square_lng
         
        path_distances = self.R * np.sqrt(square_sum)
         
        return path_distances  
        
         
    def calculate_path_gradients(self, elevations, distances):
        """
        Get the approximate gradients of every point on the path.
        
        elevations: [N][elevations]
        distances: [N-1][distances]
        
        Returns:
            - gradients[N-1]

        Note:
            - gradient > 0 corresponds to uphill
            - gradient < 0 corresponds to downhill
        """
    
        #subtract every next elevation with the previous elevation to 
        # get the difference in elevation
        # [1 2 3 4 5]
        # [5 1 2 3 4] -
        # -------------
        #   [1 1 1 1]
        offset = np.roll(elevations, 1)
        delta_elevations = (elevations - offset)[1:]
       
        #Divide the difference in elevation to get the gradient
        # gradient > 0: uphill
        # gradient < 0: downhill
        gradients = delta_elevations / distances
        
        return gradients
        
         
    def calculate_current_gradient(self):
        """
        Get the gradient of the point closest to the current location
        """
        
        return gradients[self.current_index]

    
    def calculate_current_heading(self):
        """
        From the current and previous coordinate, calculate the current bearing of the vehicle.
        """

        if self.current_index - 1 < 0:
            coord_1 = self.path[self.current_index + 1]
            coord_2 = self.path[self.current_index]
        else:
            coord_1 = self.path[self.current_index]
            coord_2 = self.path[self.current_index - 1]

        y = math.sin(math.radians(coord_2[1] - coord_1[1])) * \
                math.cos(math.radians(coord_2[0]))

        x = math.cos(math.radians(coord_1[0])) * \
                math.sin(math.radians(coord_2[0])) - \
            math.sin(math.radians(coord_1[0])) * \
                math.sin(math.radians(coord_2[0])) * \
                   math.cos(math.radians(coord_2[1] - coord_1[0])) 

        theta = math.atan2(y, x)

        bearing = ((theta * 180)/(math.pi) + 360) % 360

        return bearing 
         
         
    def update_vehicle_position(self, incremental_distance):
        """
        Returns the closest coordinate to the current coordinate
        
        incremental_distance: distance in m covered in the latest tick
        
        Returns: The new index of the vehicle
        """
 
        additional_distance = self.distance_remainder + incremental_distance

        #while the index of position can still be advanced
        while additional_distance > 0:

            #subtract contributions from every new index
            additional_distance = additional_distance - \
                                    self.path_distances[self.current_index]

            #advance the index
            self.current_index = self.current_index + 1

        #backtrack a bit
        self.distance_remainder = additional_distance + \
                                self.path_distances[self.current_index - 1]
        self.current_index = self.current_index - 1

        return self.current_index


    def update_path(self, origin_coord, dest_coord, waypoints):
        """
        Returns a path between the origin coordinate and the destination coordinate,
            passing through a group of optional waypoints.

        origin_coord: A numpy array [latitude, longitude] of the starting coordinate
        dest_coord: A numpy array [latitude, longitude] of the destination coordinate
        waypoint: A numpy array [n][latitude, longitude], where n<=10

        Returns: A numpy array [n][latitude, longitude], marking out the path.

        https://developers.google.com/maps/documentation/directions/start
        """

        #set up URL
        url_head = "https://maps.googleapis.com/maps/api/directions/json?origin={},{}&destination={},{}".format(origin_coord[0], origin_coord[1], dest_coord[0], dest_coord[1])
    
        url_waypoints = ""
        if len(waypoints) != 0:
            
            url_waypoints="&waypoints="

            if len(waypoints) > 10:
                print("Too many waypoints; Truncating to 10 waypoints total")
                waypoints = waypoints[0:10]
            
            for waypoint in waypoints:
                
                url_waypoints = url_waypoints + "via:{},{}|".format(waypoint[0],\
                                waypoint[1])

            url_waypoints = url_waypoints[:-1]

        url_end = "&key={}".format(self.api_key)

        url = url_head + url_waypoints + url_end

        print("url: {}".format(url))

        #HTTP GET
        r = requests.get(url)
        response = json.loads(r.text)

        path_points = []

        #If a route is found,
        if response['status'] == "OK":
            print("A route was found.")

            #Pick the first route in the list of available routes
            #A route consists of a series of legs
            for leg in response['routes'][0]['legs']:

                #Every leg contains an array of steps.
                for step in leg['steps']:
                
                    #every step contains an encoded polyline
                    polyline_raw = step['polyline']['points']
                    polyline_coords = polyline.decode(polyline_raw)
                    path_points = path_points + polyline_coords

        else:
            print("No route was found: {}".format(response['status']))

        return np.array(path_points)


