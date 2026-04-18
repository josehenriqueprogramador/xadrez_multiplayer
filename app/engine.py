import chess
import chess.engine
import math

engine = chess.engine.SimpleEngine.popen_uci("stockfish")

def evaluate_position(fen: str):
    board = chess.Board(fen)

    info = engine.analyse(board, chess.engine.Limit(time=0.3))
    score = info["score"].white()

    if score.is_mate():
        return 1.0 if score.mate() > 0 else 0.0
    else:
        cp = score.score()
        prob = 1 / (1 + math.exp(-cp / 300))
        return prob, cp

def classify_move(cp_before, cp_after):
    diff = cp_after - cp_before

    if diff > 150:
        return "!! Excelente"
    elif diff > 50:
        return "! Boa"
    elif diff > -50:
        return "OK"
    elif diff > -150:
        return "?! Imprecisão"
    elif diff > -300:
        return "? Erro"
    else:
        return "?? Blunder"
