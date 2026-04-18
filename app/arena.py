import chess

def initial_state():
    return {
        "fen": chess.Board().fen(),
        "turno": "w",
        "vitoria": False,
        "modo": "pvp"
    }

def apply_move(state, move_uci):
    board = chess.Board(state["fen"])
    move = chess.Move.from_uci(move_uci)

    if move in board.legal_moves:
        board.push(move)
        state["fen"] = board.fen()
        state["turno"] = "w" if board.turn else "b"

        if board.is_checkmate():
            state["vitoria"] = True

        return True
    return False
