from fastapi import FastAPI, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import json
import chess
import chess.svg

from app.arena import initial_state, apply_move
from app.manager import RoomManager
from app.engine import evaluate_position, classify_move

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
manager = RoomManager()

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/game/{room_id}")
async def game(request: Request, room_id: str):
    return templates.TemplateResponse("game.html", {"request": request, "room": room_id})

@app.websocket("/ws/{room_id}")
async def ws(websocket: WebSocket, room_id: str):
    await websocket.accept()
    room = manager.get_room(room_id)

    if not room["state"]:
        room["state"] = initial_state()
        room["history"] = []
        room["evals"] = []

    room["connections"].append(websocket)

    async def broadcast():
        board = chess.Board(room["state"]["fen"])
        svg = chess.svg.board(board=board)

        prob, cp = evaluate_position(room["state"]["fen"])
        room["evals"].append(cp)

        data = {
            "state": room["state"],
            "board": svg,
            "prob": prob,
            "evals": room["evals"],
            "history": room["history"]
        }

        alive = []
        for ws in room["connections"]:
            try:
                await ws.send_text(json.dumps(data))
                alive.append(ws)
            except:
                pass
        room["connections"] = alive

    await broadcast()

    try:
        while True:
            move = await websocket.receive_text()

            board = chess.Board(room["state"]["fen"])
            prob_before, cp_before = evaluate_position(room["state"]["fen"])

            if apply_move(room["state"], move):
                prob_after, cp_after = evaluate_position(room["state"]["fen"])

                label = classify_move(cp_before, cp_after)

                room["history"].append({
                    "move": move,
                    "eval": cp_after,
                    "label": label
                })

                await broadcast()

    except:
        room["connections"].remove(websocket)
