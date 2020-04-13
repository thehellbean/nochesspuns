import tornado.websocket
import tornado.web
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import os

db = sqlalchemy.create_engine('postgresql://inet_admin:'+ os.environ["DB_PASS"] + '@localhost/inetproject')
Session = sessionmaker(bind=db)