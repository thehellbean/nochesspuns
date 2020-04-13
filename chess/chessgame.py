from chess import Session, models
import datetime
from math import floor

class ChessGame:
    def __init__(self):
        self.load_default_board()
        self.players = []

        # Index 0 = white's timer, last move
        # Index 1 = black's timer, last move
        self.timer = [0, 0]

        # Datetime object representing the time of the last move
        self.lastmove = []
        self.move_cache = []
        # Acts as index in player array
        # 0 = white, 1 = black
        self.active_player = 0
        self.active = False
        self.winner = None
        self.movenr = 1

    def load_default_board(self):
        self.board = []
        for i in range(8):
            self.board.append([" "]*8)
        for x in range(8):
            # Capital letters = white
            # Non-capital letters = black
            self.board[6][x] = "p"
            self.board[1][x] = "P"

        # White pieces
        self.board[0][0] = self.board[0][7] = "R"
        self.board[0][1] = self.board[0][6] = "N"
        self.board[0][2] = self.board[0][5] = "B"
        self.board[0][3] = "Q"
        self.board[0][4] = "K"

        # Black pieces
        self.board[7][0] = self.board[7][7] = "r"
        self.board[7][1] = self.board[7][6] = "n"
        self.board[7][2] = self.board[7][5] = "b"
        self.board[7][3] = "q"
        self.board[7][4] = "k"

    def make_move(self, player, fromCoord, toCoord):
        # Validates and executes a move from player (0 = white, 1 = black)
        # Does nothing if it's not that player's turn
        # Takes player ID as an argument

        # Coordinate structure is an int of the form YX, e.g 70 represents A8, 77 is H8
        print(player)
        playerSide = self.players.index(player)
        print(playerSide, self.active_player)

        try:
            if self.check_flag():
                # Player is out of time, no reason to keep going
                return
        except:
            # No last move, i.e player's first move of the game
            pass

        # TODO: ADD SPECIAL MOVES AND TAKING PIECES
        moves = self.possible_moves(fromCoord)
        validMove = (toCoord // 10, toCoord % 10) in set(moves)
        piece = self.board[fromCoord // 10][fromCoord % 10]
        piece_set = "RBQKNP" if self.active_player == 0 else "rbqknp"
        owns_piece = piece in piece_set

        # Test move to see if it puts current player in check
        mem_piece = self.board[toCoord // 10][toCoord % 10]
        self.board[toCoord // 10][toCoord % 10] = self.board[fromCoord // 10][fromCoord % 10]
        self.board[fromCoord // 10][fromCoord % 10] = " "
        

        if playerSide == self.active_player and validMove and owns_piece and not self.is_checked(): 
            print("Made move")
            print(fromCoord, toCoord)
            self.timer[self.active_player] += self.increment

            move = models.Move(movenr=self.movenr, game_id=self.game_id, user_id=player, move_from=fromCoord, move_to=toCoord)
            self.movenr += 1
            self.move_cache.append(move)
            validMove = True

            # For tracking time between moves
            self.lastmove[self.active_player] = datetime.datetime.utcnow() 
            # Switch player
            self.active_player = (self.active_player + 1) % 2
            if(self.is_checked() and self.checkmate()):
                print("Checkmate")
                return 2
        else:
            self.board[fromCoord // 10][fromCoord % 10] = self.board[toCoord // 10][toCoord % 10]
            self.board[toCoord // 10][toCoord % 10] = mem_piece 
            validMove = False

        return 1 if validMove else 0

    def save_moves(self):
        session = Session()
        for move in self.move_cache:
            session.add(move)
        self.move_cache = []
        session.commit()
        session.close()

    def get_timer(self):
        # Updates timer and returns value
        now = datetime.datetime.utcnow()
        delta = floor((now - self.lastmove[self.active_player]).total_seconds())
        self.timer[self.active_player] -= delta
        self.lastmove[self.active_player] = now

        return self.timer

    def load_game(self, game_id):
        session = Session()
        now = datetime.datetime.utcnow()
        self.lastmove = [now, now]
        self.game_id = game_id
        res = session.query(models.Game.white, models.Game.black, models.Game.winner, models.Game.increment).filter(models.Game.id==game_id).one()
        self.players = [res.white, res.black]
        self.process_moves(game_id, session)
        if res.winner is None:
            self.increment = res.increment
            self.load_timer(game_id, session)

    def save_timer(self):
        session = Session()
        now = datetime.datetime.utcnow()
        if self.active_player == 0:
            self.timer[0] -= floor((now - self.lastmove[0]).total_seconds())
        else:
            self.timer[1] -= floor((now - self.lastmove[1]).total_seconds())
        try:
            whiteState = session.query(models.TimerState).filter((models.TimerState.game_id==self.game_id) & (models.TimerState.user_id==self.players[0])).one()
            blackState = session.query(models.TimerState).filter((models.TimerState.game_id==self.game_id) & (models.TimerState.user_id==self.players[1])).one()
            whiteState.time_recorded = now
            whiteState.state = self.timer[0]
            blackState.time_recorded = now
            blackState.state = self.timer[1]
        except:
            whiteState = models.TimerState(user_id=self.players[0], game_id=self.game_id, time_recorded=now, state=self.timer[0])
            blackState = models.TimerState(user_id=self.players[1], game_id=self.game_id, time_recorded=now, state=self.timer[1])
        session.add(whiteState)
        session.add(blackState)
        session.commit()
        session.close()

    def check_flag(self):
        # Flagging is the chess term for running out of time

        delta = (datetime.datetime.utcnow() - self.lastmove[self.active_player]).total_seconds()
        self.timer[self.active_player] -= floor(delta)

        # Check for flagging, end game if someone flagged
        if self.timer[0] <= 0:
            self.set_winner(1)
            return True
        elif self.timer[1] <= 0:
            self.set_winner(0)
            return True
        else:
            return False

    def update_ratings(self, winner, loser):
        # Compute and save ratings for a winner and loser
        # Parameters are user IDs
        session = Session()
        loser = session.query(models.User).filter(models.User.id==loser).one()
        winner = session.query(models.User).filter(models.User.id==winner).one()

        qw = 10 ** (winner.rating / 400)
        ql = 10 ** (winner.rating / 400)
        winnerExp = qw / (qw + ql)
        loserExp = ql / (qw + ql)

        loser.rating = loser.rating + 32 * (-loserExp)
        winner.rating = winner.rating + 32 * (1 - winnerExp)

        session.add(loser)
        session.add(winner)
        session.commit()
        session.close()
        
    def set_winner(self, winner):
        print("Someone won!")
        self.winner = winner
        self.active = False
        session = Session()
        game = session.query(models.Game).filter(models.Game.id==self.game_id).one()
        game.winner = self.players[winner]
        self.update_ratings(game.winner, self.players[(winner + 1) % 2])
        session.add(game)
        session.commit()
        session.close()

    def load_timer(self, game_id, session):
        # Loads a saved timer state from the database and updates with the amount of time passed since then
        timers = session.query(models.TimerState).filter(models.TimerState.game_id==game_id).all()
        for timer in timers:
            delta = (datetime.datetime.utcnow() - timer.time_recorded).total_seconds()

            # It's this player's turn, so the time ticked since then is on their clock
            if self.players[self.active_player] == timer.user_id:
                self.timer[self.active_player] = timer.state - floor(delta)
            else:
                self.timer[(self.active_player + 1) % 2] = timer.state

        self.check_flag()

    def process_moves(self, game_id, session):
        # Updates the game state according to all moves in the given game
        # This includes the game board and whose turn it is
        moves = session.query(models.Move.move_from, models.Move.move_to, models.Move.user_id, models.Move.movenr).filter(models.Move.game_id==game_id).order_by(models.Move.movenr.asc()).all()

        # If no moves have been made active player defaults to 0 (white)
        if moves:
            lastMove = moves[-1]
            self.movenr = lastMove.movenr + 1

            # Current player is the player who didn't make the last move
            print(self.players, lastMove.user_id)
            self.active_player = lastMove.movenr % 2

        for i in moves:
            self.board[i.move_to // 10][i.move_to % 10] = self.board[i.move_from // 10][i.move_from % 10]
            self.board[i.move_from // 10][i.move_from % 10] = " "

    def toString(self):
        output = ""
        for y in range(7, -1, -1):
            for x in range(8):
                output += self.board[y][x]
            
        return output

    def out_of_bounds(self, yp, xp):
        return (yp > 7 or yp < 0) or (xp > 7 or xp < 0)

    def possible_moves(self, fromCoord):
        # Returns all the possible moves for every piece that might be on the square fromCoord
        moves = []
        # Straight moves for rook
        straight = [(-1, 0), (1,0), (0, -1), (0, 1)]
        # Diagonal moves for bishop
        diagonal = [(-1, -1), (1, 1), (-1, 1), (1, -1)]
        # Whatever moves for knight
        knight = [(2, 1), (1, 2)]

        y = fromCoord // 10
        x = fromCoord % 10
        piece = self.board[y][x]

        if (piece.lower() == 'r'):
            for dir in straight:
                for i in range(1,8):
                    yp = y + dir[0] * i
                    xp = x + dir[1] * i 
                    if(self.out_of_bounds(yp, xp)):
                        break
                    moves.append((yp, xp))
                    if(self.board[yp][xp] != " "):
                        break
        elif (piece.lower() == 'b'):
            for dir in diagonal:
                for i in range(1,8):
                    yp = y + dir[0] * i
                    xp = x + dir[1] * i 
                    if(self.out_of_bounds(yp, xp)):
                        break
                    moves.append((yp, xp))
                    if(self.board[yp][xp] != " "):
                        break
        
        elif (piece.lower() == 'q'):
            # Combine straight and diagonal moves for queen
            queen = list(set(straight + diagonal))
            for dir in queen:
                for i in range(1, 8):
                    yp = y + dir[0] * i
                    xp = x + dir[1] * i 
                    if(self.out_of_bounds(yp, xp)):
                        break
                    moves.append((yp, xp))
                    if(self.board[yp][xp] != " "):
                        break

        elif (piece.lower() == 'n'):
            # It just so happens that we can reuse the diagonal directions from
            # the bishop to get all possible moves for the knight
            for dir in diagonal:
                for move in knight:
                    yp = y + dir[0] * move[0]
                    xp = x + dir[1] * move[1]
                    if(self.out_of_bounds(yp, xp)):
                        break
                    moves.append((yp, xp))

        elif (piece.lower() == 'p'):
            # Moves for both black and white pawn
            pawn =  (1, 0) if piece == 'P' else (-1, 0)
            for take in [1, -1]:
                yp = y + pawn[0]
                xp = x + pawn[1] + take
                if(not self.out_of_bounds(yp, xp) and self.board[yp][xp] != " "):
                    moves.append((yp, xp))
            # TODO create method to change pawn to other piece if at end of board
            yp = y + pawn[0]
            xp = x
            if((pawn[0] == 1 and y == 1) or (pawn[0] == -1 and y == 6)):
                if(not self.out_of_bounds(yp + pawn[0], xp) and self.board[yp + pawn[0]][xp] == " "):
                    moves.append((yp + pawn[0], xp))
            if(not self.out_of_bounds(yp, xp) and self.board[yp][xp] == " "):
                moves.append((yp, xp))

        elif (piece.lower() == 'k'):
            # King can move all directions but only one step
            king = diagonal + straight
            for dir in king:
                yp = y + dir[0]
                xp = x + dir[1]
                if(self.out_of_bounds(yp, xp)):
                    break
                moves.append((yp, xp))

        # Filter out moves where we try to take our own piece
        moves = list(filter(lambda l: (self.board[l[0]][l[1]].isupper() != self.board[y][x].isupper()) or self.board[l[0]][l[1]] == " " , moves))
        return moves

    def is_checked(self):
        # Checks if the current state for the board puts @player in check
        # If player = 0, white is playing
        k = 'K' if self.active_player == 0 else 'k'
        pieces = "nkqrpb" if self.active_player == 0 else "NKQRPB"
        king = (-1, -1)
        all_moves = []
        # Go through the board and check possible moves for opposing player
        for y in range(0,8):
            for x in range(0,8):
                if(self.board[y][x] == k):
                    king = (y, x)
                if (self.board[y][x] in set(pieces)):
                    all_moves = all_moves + self.possible_moves(y * 10 + x)
        return king in set(all_moves)

    def checkmate(self):
        # Naive function that returns if there are any possible moves left for player
        pieces = "NKQRPB" if self.active_player == 0 else "nkqrpb"
        # Go through the board and check possible moves for opposing player
        for y in range(0,8):
            for x in range(0,8):
                if (self.board[y][x] in set(pieces)):
                    moves = self.possible_moves(y*10 + x)
                    for move in moves:
                        mem_piece = self.board[move[0]][move[1]]
                        self.board[move[0]][move[1]] = self.board[y][x]
                        self.board[y][x] = " "
                        checked = self.is_checked()
                        self.board[y][x] = self.board[move[0]][move[1]]
                        self.board[move[0]][move[1]] = mem_piece
                        if(not checked):
                            return False
                        
        return True
        

