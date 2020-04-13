# NoChessPuns

This is a backend server for a multiplayer chess application written in Python using Tornado.

It features a REST API for managing user accounts and creating game lobbies. When a user is in an active game (as a player or spectator) websockets are used to communicate game state.

Game timers are tracked so that even if all users leave a game the timers will keep counting down, and a game can be resumed as long as the players have time left on their clocks.
