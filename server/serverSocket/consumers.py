import json
from server.serverActions import *
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from ..examples import fastest_time_given_distance as simulation

# An instance of SocketConsumer will be created for every client that connects to the WebSocket
class SocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):  # Executed when a client connects to the websocket to initialize the consumer
        self.room_name = self.scope["url_route"]["kwargs"]
        self.room_group_name = "mainRoom"

        # Joins room "mainRoom" which allows it to listen/send messages
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()  # Completes the connection

    async def disconnect(self, close_code):  # Executes when a client disconnects
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Executed when a message is sent over the WebSocket, expects a JSON message which is parsed then handled
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        requestType = text_data_json['requestType']  # Gets requestType as string from parsed JSON data

        if requestType == "date":  # If request is for the date, get the date and send it to the layer
            data = RequestDate()

            # first arg 'deliver_data' calls a function, following arg corresponds to param 'event' of called function
            await self.channel_layer.group_send(self.room_group_name, {"type": "deliver_data", "message": data})

    async def deliver_data(self, event):
        message = event["message"]

        # Send data to WebSocket, typically consumer clients receive data with {websocket}.onmessage
        await self.send(text_data=json.dumps({"message": message}))

    async def get_simulation_data(self):
        rawData = simulation.GetOptimizedSimulation()
        data = json.dumps(rawData)

        # Send data to WebSocket, typically consumer clients receive data with {websocket}.onmessage
        await self.send(text_data=json.dumps({"message": rawData}))
