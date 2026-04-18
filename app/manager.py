class RoomManager:
    def __init__(self):
        self.rooms = {}

    def get_room(self, room_id):
        if room_id not in self.rooms:
            self.rooms[room_id] = {
                "connections": [],
                "state": None
            }
        return self.rooms[room_id]
