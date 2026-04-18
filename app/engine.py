import chess
import chess.engine

engine = chess.engine.SimpleEngine.popen_uci("stockfish")

def get_ai_move(fen: str):
    board = chess.Board(fen)
    result = engine.play(board, chess.engine.Limit(time=0.3))
    return result.move.uci()
