class BGPMessage:
    def __init__(self):
        self.message = None
        self.peer = {
            'address': None
            , 'asn': None
        }
        self.time = None
        self.fields = {}
        self.flags = {}
