from fastapi import FastAPI, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import json
import chess
import chess.svg

from app.arena import initial_state, apply_move
from app.manager import RoomManager
from app.engine import get_ai_move

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

    room["connections"].append(websocket)

    async def broadcast():
        board = chess.Board(room["state"]["fen"])
        svg = chess.svg.board(board=board)

        data = {
            "state": room["state"],
            "board": svg
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

            if apply_move(room["state"], move):
                if room["state"]["modo"] == "ai" and not room["state"]["vitoria"]:
                    ai_move = get_ai_move(room["state"]["fen"])
                    apply_move(room["state"], ai_move)

                await broadcast()

    except:
        room["connections"].remove(websocket)
