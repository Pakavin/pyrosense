class Compartment:
    def __init__(self, room_number):
        self.room_number = room_number
        self.ignition_prob = 0
        self.ignition_time = float('inf')
        self.flashover_prob = 0
        self.flashover_time = float('inf')
        self.fully_developed = False

class FireModel:
    def __init__(self, n_floor, n_room, T):
        self.n_floor = n_floor
        self.n_room = n_room
        self.T = T
        self.dT = T / 1000
        self.L = 2 * T