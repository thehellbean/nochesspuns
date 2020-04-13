import tornado.ioloop
import tornado.web
from chess import api, roomhandler, websocket

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

def make_app():
    rh = roomhandler.RoomHandler()
    settings = {
        "cookie_secret": "PLACEHOLDER_COOKIE_SECRET",
        "xsrf_cookies": True
    }
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/websocket", websocket.ChessSocket, {"room_handler": rh}),
        (r"/api/user/?(\d*)/?", api.UserAPIHandler),
        (r"/api/login/?", api.LoginHandler),
        (r"/api/logout/?", api.LogoutHandler),
        (r"/api/games/?(\d*)/?", api.GameAPIHandler),
        (r"/xsrf/?", api.XSRFCookieHandler)
    ], **settings)

if __name__ == "__main__":
    app = make_app()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()