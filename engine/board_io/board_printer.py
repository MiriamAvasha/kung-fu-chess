from model.game_state import GameState


class BoardPrinter:
    def print_board(self, game_state: GameState):
        for row in game_state.board.to_token_grid():
            print(" ".join(row))
