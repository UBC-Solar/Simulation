from datetime import datetime

import pickle


# A class which holds an id which is intended to correspond to a type of requested data by a client for the backend
def RequestDate():
    """
    @rtype: str
    """

    data = datetime.now()
    return data.strftime("%m/%d/%Y, %H:%M:%S")


class ServerRequest:
    def __init__(self, requestid):
        self.requestID = requestid

    def serialize(self):  # A method to serialize the class so it can be sent as binary to the backend
        return pickle.dumps(self)


# A class which holds data which is intended to fulfill a request for data by the client
class ServerResponse:
    def __init__(self, data):
        self.data = data

    def serialize(self):  # A method to serialize the class so it can be sent as binary to the client
        return pickle.dumps(self)