import tornado.websocket
from chess import Session, chessgame
from chess.models import Game, User, TimerState
from chess.api import BaseHandler
import datetime
import json

class ChessSocket(tornado.websocket.WebSocketHandler, BaseHandler):
    def initialize(self, room_handler):
        self.rh = room_handler
        self.room = 0
        self.handlers = {"roomEnter": self.roomEnter, "addMessage": self.addMessage, "startGame": self.startGame, "move": self.move, "timeout": self.timeout}
        self.board = chessgame.ChessGame()
        self.active = False

    def open(self):
        print("Opened connection")

    def timeout(self):
        if self.active:
            self.board.check_flag()

    def roomEnter(self, data):
        print("Received roomEnter")
        session = Session()
        try:
            game = session.query(Game).filter(Game.id==data).one()
            self.rh.join(self, data)
        except:
            self.write_message(json.dumps({"success": False, "data": {"message": "Room name invalid"}}))
            return
        if (game.started_on is not None):
            game.load_player_names()
            print("Setting self to active")
            self.active = True
            if len(self.rh.rooms[data]) > 1:
                self.board = self.rh.rooms[data][0].board
            else:
                self.board.load_default_board()
                self.board.load_game(data)
            responseData = {"data": {"activeplayer": self.board.active_player, "timer": self.board.get_timer(), "board": self.board.toString(),\
            "white": game.white, "black": game.black, "timestamp": datetime.datetime.utcnow().timestamp(),\
            "white_name": game.white_name, "black_name": game.black_name}, "event": "gameData"}
        else:
            if game.white is None:
                player = game.black
            else:
                player = game.white
            responseData = {"data": {"challenger": player}, "event": "lobbyData"}
        self.room = data
        self.write_message(json.dumps(responseData))
        session.close()
        print("Joined room", data)

    def startGame(self, data):
        session = Session()
        game = session.query(Game).filter(Game.id==self.room).one()
        print("Started on", game.started_on)
        if self.current_user and game.started_on is None:
            if game.white is None:
                game.white = self.current_user.id
            else:
                game.black = self.current_user.id
            game.started_on = datetime.datetime.utcnow()
            wState = TimerState(user_id=game.white, game_id=self.room, state=game.start_clock, time_recorded=game.started_on)
            bState = TimerState(user_id=game.black, game_id=self.room, state=game.start_clock, time_recorded=game.started_on)
            wName = session.query(User.username).filter(User.id==game.white).one().username
            bName = session.query(User.username).filter(User.id==game.black).one().username
            session.add(game)
            session.add(wState)
            session.add(bState)
            session.commit()
            self.board.load_game(game.id)
            self.rh.to(self.room, "startGame", {"white_name": wName, "black_name": bName,\
                "white": game.white, "black": game.black, "clock": game.start_clock, "board": self.board.toString()})
            self.active = True
        session.close()

    def move(self, data):
        if self.active and self.current_user:
            print("Sending message to ", self.room)
            move_result = self.board.make_move(self.current_user.id, data["moveFrom"], data["moveTo"])
            if move_result == 1:
                self.rh.to(self.room, "move", self.board.toString())
            if move_result == 2:
                self.rh.to(self.room, "checkmate", self.board.toString())

    def addMessage(self, data):
        self.rh.to(self.room, "message", data)
        print("Sent messsage to", self.room)

    def on_message(self, message):
        try:
            payload = json.loads(message)
        except:
            print("Received invalid message")
            return

        print(payload)
        if payload["event"] in self.handlers:
            self.handlers[payload["event"]](payload["data"])

    def on_close(self):
        if self.room:
            if len(self.rh.rooms[self.room]) == 1:
                self.board.save_moves()
            self.rh.rooms[self.room].remove(self)
        if self.active:
            self.board.save_timer()
        print("Closed connection")