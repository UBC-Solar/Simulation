#!/usr/bin/env python

"""
A class to extract local and path weather predictions such as wind_speed, 
    wind_direction, cloud_cover and weather type
"""

import requests
import json
import polyline
import time
import numpy as np


class WeatherForecasts():


    def __init__(self, api_key, coords, time):
        """
        Initializes the instance of a WeatherForecast class 

        api_key: A personal openweatherapi key to access weather forecasts
        coords: A numpy array of [latitude, longitude]
        time: The UNIX time of initialization
        """

        self.key = api_key

        self.coords = coords
        self.last_updated_time = time

        coords = self.cull_dataset(coords)

        self.weather_forecast = self.update_path_weather_forecast(coords,\
                                     self.last_updated_time)

    def cull_dataset(self, coords):
        """
        As we currently have a limited number of API calls(60) every minute with the 
            current Weather API, we must shrink the dataset significantly. As the
            OpenWeatherAPI models have a resolution of between 2.5 - 70 km, we will
            go for a resolution of 25km. Assuming we travel at 100km/h for 12 hours,
            1200 kilometres/25 = 48 API calls

        As the Google Maps API has a resolution of around 40m between points, 
            we must cull at 625:1    
        """

        return coords[::625]

    def update_local_weather_forecast(self, coord):
        """
        Passes in a single coordinate, returns the hourly weather forecast 
            for the coordinate

        coords: A numpy array of [latitude, longitude]
        
        Returns:
        - A numpy array [24][7]
        - [24]: hours from current time
        - [7]: (latitude, longitude, dt, wind_speed, wind_direction,
                    cloud_cover, description_id)

        For reference to the API used:
        - https://openweathermap.org/api/one-call-api
        """

        url = "https://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&exclude=current,minutely,daily&appid={}".format(coord[0], coord[1], self.key)

        r = requests.get(url)
        response = json.loads(r.text)

        weather_array = np.zeros((24, 7))

        for i in range(24):
            
            weather_array[i][0] = coord[0]
            weather_array[i][1] = coord[1]
            weather_array[i][2] = response["hourly"][i]["dt"]
            weather_array[i][3] = response["hourly"][i]["wind_speed"]
            weather_array[i][4] = response["hourly"][i]["wind_deg"]
            weather_array[i][5] = response["hourly"][i]["clouds"]
            weather_array[i][6] = response["hourly"][i]["weather"][0]["id"]  

        return weather_array


    def update_local_current_weather(self, coord, time):
        """
        Passes in a single coordinate, returns the current weather for the
            coordinate

        coords: A numpy array of [latitude, longitude]
    
        Returns:
        - A numpy array [7]
        - [7]: (latitude, longitude, dt, wind_speed, wind_direction,
                    cloud_cover, description_id)

        """

        url = "https://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&exclude=minutely,daily,hourly&appid={}".\
            format(coord[0], coord[1], self.key)
        r = requests.get(url)

        response = json.loads(r.text) 

        current_weather = np.zeros(7)

        current_weather[0] = coord[0]
        current_weather[1] = coord[1]
        current_weather[2] = response["current"]["dt"]
        current_weather[3] = response["current"]["wind_speed"]
        current_weather[4] = response["current"]["wind_deg"]
        current_weather[5] = response["current"]["clouds"]
        current_weather[6] = response["current"]["weather"][0]["id"]

        return current_weather


    def update_path_weather_forecast(self, coords, last_updated_time):
        """
        Passes in a list of coordinates, returns the hourly weather forecast
            for each of the coordinates
        
        coords: A numpy array of [coord_index][2]
        - [2] => [latitude, longitude]
        
        Returns: 
        - A numpy array [coord_index][24][7]
        - [coord_index]: the index of the coordinates passed into the function
        - [24]: hours from self.last_updated_time
        - [7]: (latitude, longitude, wind_speed, wind_direction, 
                     cloud_cover, precipitation, description)

        Modifies: self.weather_forecast
        """
        
        num_coords = len(coords)
        
        weather_forecast = np.zeros((num_coords, 24, 7))
        
        for i, coord in enumerate(coords):
       
            #If the limit has not been reached, then continue getting the hourly forecast 
            if i < 10:
                weather_forecast[i] = self.update_local_weather_forecast(coord)
            else:
                weather_forecast[i] = np.zeros((24,7))
                
  
        self.coords = coords 
        self.last_updated_time = last_updated_time
        self.weather_forecast = weather_forecast

        return weather_forecast 

 
    def get_path_weather_forecast(self):
        """
        Passes in a list of coordinates, returns the hourly weather forecast
            for each of the coordinates without calculating
        
        coords: A numpy array of [coord_index][2]
        - [2] => [latitude, longitude]
        
        Returns: 
        - A numpy array [coord_index][24][7]
        - [coord_index]: the index of the coordinates passed into the function
        - [24]: hours from self.last_updated_time
        - [7]: (latitude, longitude, wind_speed, wind_direction, 
                     cloud_cover, precipitation, description)
        """

        return self.weather_forecast

    #TODO: function which takes in a list of coordinates, and returns a list of
    #       weather_forecast indices which are closest to the coordinate

    #TODO: function which takes in a list of weather_forcast indices, and returns the 
    #       wind speed for all the coordinates there

    def get_closest_weather_forecast(self, coord):
        """
        Passes in a single coordinate, calculates the closest coordinate to that
        coordinate, returns the forecast for the closest location

        coord: A numpy array of [latitude, longitude]

        Returns:
        - A numpy array [24][7]
        - [24]: hours from the self.last_updated_time
        - [7]: (latitude, longitude, wind_speed, wind_direction, 
                    cloud_cover, precipitation, description)
        """

        temp_1 = np.full((len(self.coords),2), coord)
        temp_2 = self.coords - temp_1
        temp_3 = np.square(temp_2)
        temp_4 = np.sum(temp_3, axis=1)
        temp_5 = np.sqrt(temp_4)

        return weather_forecast[temp5.index(max(temp_5))]


    def get_last_updated_time(self):
        """
        Returns the UNIX time in which the list of coordinates comprising the 
            current route was updated
        """    

        return self.last_updated_time


    def get_directional_wind_speed(self, vehicle_azimuth, wind_speed, wind_direction):
        """
        Returns the wind speed in m/s, in the direction opposite to the
            bearing of the vehicle

        vehicle_bearing: The azimuth angle that the vehicle is moving in, in degrees
        wind_speed: The absolute speed of the wind in m/s
        wind_direction: The azimuth angle of the wind, in degrees

        Returns: The wind speed in the direction opposite to the bearing of the vehicle
        """

        #if driving at heading x clockwise from north
        #wind direction at heading y clockwise from north

        return wind_speed * (math.cos(math.radians(wind_direction - vehicle_azimuth)))
        

    def get_weather_advisory(self, ID):
        """
        Returns a string indicating the type of weather to expect, from the standardized
            weather code passed as a parameter

        https://openweathermap.org/weather-conditions#Weather-Condition-Codes-2
        """

        if ID >= 200 and ID < 300:
            return "Thunderstorm"
        elif ID >= 300 and ID < 500:
            return "Drizzle" 
        elif ID >= 500 and ID < 600:
            return "Rain"
        elif ID >= 600 and ID < 700:
            return "Snow"
        elif ID == 800:
            return "Clear"
        else:
            return "Unknown"

