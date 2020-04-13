from chess import models, Session
from chess.models import User, Game, UserSession
from tornado import web, escape
import json
from sqlalchemy import or_
import traceback

class BaseHandler(web.RequestHandler):
    # This will define current_user in all classes inheriting from BaseHandler
    def get_current_user(self):
        try:
            cookieToken = str(self.get_secure_cookie("authtoken"), "utf-8")
            cookieID = str(self.get_secure_cookie("authid"), "utf-8")
            session = Session()
            token = session.query(UserSession).filter(UserSession.token==cookieToken, UserSession.user_id==cookieID).one()
            if token.verify():
                return session.query(User).filter(User.id==cookieID).one()
        except:
            return None

class XSRFCookieHandler(BaseHandler):
    def get(self):
        print(self.xsrf_token)
        self.write(self.xsrf_token)

class GameAPIHandler(BaseHandler):
    # Retrieve information about games/a single game
    def get(self, slug):
        session = Session()

        # Request to /games/
        if not slug:
            # Games without a winner are still in progress/not started
            challenges = session.query(Game).filter(Game.started_on==None).all()
            challengeList = []
            for challenge in challenges:
                challengeDict = challenge._asdict()
                challengeDict["user"] = session.query(User.username, User.rating).filter((User.id==challenge.white) | (User.id==challenge.black)).one()._asdict()
                challengeList.append(challengeDict)

            activeGames = session.query(Game).filter((Game.started_on != None) & (Game.winner==None)).all()
            activeGamesList = []
            for game in activeGames:
                game.load_player_names()
                gameDict = game._asdict()
                activeGamesList.append(gameDict)

            self.write(json.dumps({"challenges": challengeList, "activeGames": activeGamesList}))

        # Request to /games/\d+
        else:
            game = session.query(Game).filter(Game.id==slug).one()
            game.load_player_names()
            game = game._asdict()
            self.write(json.dumps(game))
        session.close()

    # Create a new game
    def post(self, slug):
        if self.current_user:
            params = escape.json_decode(self.request.body)
            print(params)
            if (params["side"] is not None and params["clock"] is not None and params["increment"] is not None):    
                session = Session()
                game = Game(start_clock=params["clock"], increment=params["increment"])
                if params["side"] == "black":
                    game.black = self.current_user.id
                else:
                    game.white = self.current_user.id
                session.add(game)
                session.commit()
                print("Game created", game.id)
                self.write(json.dumps({"success": True, "id": game.id}))
                session.close()
            else:
                self.write(json.dumps({"success": False}))
        else:
            print("Not logged in")
            self.write(json.dumps({"success": False}))

class UserAPIHandler(BaseHandler):
    def get(self, slug):
        session = Session()
        if not slug:
            users = session.query(User.username, User.rating, User.id).order_by(User.rating.desc()).all()
            users = [c._asdict() for c in users]
            self.write(json.dumps(users))
        else:
            try:
                user = session.query(User.username, User.email).filter(User.id == slug).one()._asdict()
                activeGames = session.query(Game).filter(((Game.white==slug) | (Game.black==slug)) & (Game.winner==None) & (Game.started_on!=None)).all()
                for game in activeGames:
                    game.load_player_names()
                activeGames = [c._asdict() for c in activeGames]
                user["activeGames"] = activeGames

                endedGames = session.query(Game).filter(((Game.white==slug) | (Game.black==slug)) & (Game.winner!=None)).all()
                for game in endedGames:
                    game.load_player_names()
                endedGames = [c._asdict() for c in endedGames]
                user["endedGames"] = endedGames

                unstartedGames = session.query(Game).filter(((Game.white==slug) | (Game.black==slug)) & (Game.started_on==None)).all()
                unstartedGames = [c._asdict() for c in unstartedGames]
                user["unstartedGames"] = unstartedGames
                self.write(json.dumps(user))
            except:
                self.set_status(404)
                self.write(json.dumps({"message": "request invalid"}))
        session.close()

    def post(self, slug):
        data = escape.json_decode(self.request.body)
        username = data["username"]
        password = data["password"]
        email = data["email"]
        if not (username and password and email):
            self.write(json.dumps({"message": "missing parameters", "success": False}))
            return

        session = Session()
        newUser = User(username, email, password)
        session.add(newUser)
        session.commit()
        session.close()

        self.write(json.dumps({"success": True, "message": "Created your account. You can now sign in!"}))

class LogoutHandler(BaseHandler):
    def post(self):
        if self.current_user:
            self.set_secure_cookie("authtoken", "", expires_days=0)
            self.set_secure_cookie("authid", "", expires_days=0)
            print("Logged out")
            self.write(json.dumps({"success": True}))

class LoginHandler(BaseHandler):
    def post(self):
        if self.current_user:
            print("Already logged in")
            self.write(json.dumps({"success": False, "message": "You are already logged in, fool"}))
            return
        data = escape.json_decode(self.request.body)
        username = data["username"]
        password = data["password"]
        session = Session()
        print(username, password)
        try:
            tent = session.query(User).filter(User.username==username).one()
        except:
            print("User not found")
            self.write(json.dumps({"success": False, "message": "User/password combination not found"}))
            return
        if tent.login(password):
            newCookie = UserSession(tent.id)
            session.add(newCookie)
            session.commit()
            self.set_secure_cookie("authtoken", newCookie.token)
            self.set_secure_cookie("authid", str(tent.id))
            self.write(json.dumps({"success": True, "username": username, "id": tent.id}))
            return
        else:
            print("Wrong password")
            self.write(json.dumps({"success": False, "message": "User/password combination not found"}))
        session.close()
