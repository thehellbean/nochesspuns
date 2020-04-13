import json

class RoomHandler:
    def __init__(self):
        self.rooms = {}

    def join(self, websocket, room):
        try:
            room = int(room)
        except:
            print("Room ID is not int! ERROR ERROR ERROR")
        if room in self.rooms:
            self.rooms[room].append(websocket)
        else:
            self.rooms[room] = [websocket]

    def to(self, room, event, message=None):
        print(event, message)
        if message:
            print("Sent message to ", room, "Event:", event)
            completeMessage = {"event": event, "data": message}
        else:
            completeMessage = {"event": event}
        for toroom in self.rooms[room]:
            toroom.write_message(json.dumps(completeMessage))