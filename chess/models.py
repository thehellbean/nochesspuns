import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
import bcrypt
import datetime
import base64
from os import urandom, environ
from chess import Session

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(20))
    password = Column(String(64))

    email = Column(String(100))
    rating = Column(Integer)

    def __init__(self, username, email, plaintext):
        self.rating = 1300
        self.password = str(bcrypt.hashpw(bytes(plaintext, "utf-8"), bcrypt.gensalt()), "utf-8")
        self.email = email
        self.username = username

    def login(self, plaintext):
        return bcrypt.checkpw(bytes(plaintext, "utf-8"), bytes(self.password, "utf-8"))


class UserSession(Base):
    __tablename__ = 'usersession'

    token = Column(String(32), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    expiry_date = Column(DateTime, default=datetime.datetime.utcnow() + datetime.timedelta(days=7))

    def __init__(self, user_id):
        self.token = str(base64.b64encode(urandom(23)), "utf-8")
        self.user_id = user_id

    def verify(self):
        if self.expiry_date > datetime.datetime.utcnow():
            return True
        else:
            return False

class Move(Base):
    __tablename__ = 'move'

    movenr = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    notation = Column(String(4))
    move_from = Column(Integer)
    move_to = Column(Integer)

class Game(Base):
    __tablename__ = 'game'

    id = Column(Integer, primary_key=True)
    white = Column(Integer, ForeignKey('users.id'))
    black = Column(Integer, ForeignKey('users.id'))
    winner = Column(Integer, ForeignKey('users.id'))
    start_clock = Column(Integer)
    started_on = Column(DateTime)
    increment = Column(Integer)

    def load_player_names(self):
        session = Session()
        if self.white:
            self.white_name = session.query(User.username).filter(User.id==self.white).one().username
        else:
            self.white_name = ""
        if self.black:
            self.black_name = session.query(User.username).filter(User.id==self.black).one().username
        else:
            self.black_name = ""
        session.close()

    def _asdict(self):
        d = self.__dict__
        if d["started_on"]:
            d["started_on"] = d["started_on"].strftime("%Y-%m-%d %H:%M:%S")
        d.pop('_sa_instance_state')
        return d

class TimerState(Base):
    __tablename__ = 'timerstate'

    game_id = Column(Integer, ForeignKey('game.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    time_recorded = Column(DateTime)
    state = Column(Integer)


class Message(Base):
    __tablename__ = 'message'

    game_id = Column(Integer, ForeignKey('game.id'), primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    content = Column(String)
    date = Column(DateTime, primary_key=True, default=datetime.datetime.utcnow())


if __name__ == "__main__":
    engine = sqlalchemy.create_engine('postgresql://inet_admin:' + environ['DB_PASS'] + '@localhost/inetproject')
    Base.metadata.create_all(engine)