#!/bin/bash

echo "🚀 Atualizando projeto xadrez..."

cd ~/xadrez_multiplayer || exit

# =========================
# engine.py (ANÁLISE PROFISSIONAL)
# =========================
cat << 'PY' > app/engine.py
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
PY

# =========================
# main.py (COM HISTÓRICO + ANÁLISE)
# =========================
cat << 'PY' > app/main.py
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
PY

# =========================
# game.html (GRÁFICO + BARRA)
# =========================
cat << 'HTML' > app/templates/game.html
<html>
<body style="background:#222;color:#fff;text-align:center;">

<h2>Sala: {{room}}</h2>

<div style="display:flex; justify-content:center;">

  <div id="board"></div>

  <div style="width:60px;height:400px;margin-left:10px;border:1px solid #555;position:relative;">
    <div id="whiteBar" style="position:absolute;bottom:0;width:100%;background:#fff;"></div>
    <div id="blackBar" style="position:absolute;top:0;width:100%;background:#000;"></div>
  </div>

</div>

<canvas id="chart" width="400" height="150"></canvas>

<div id="moves"></div>

<script>
const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${protocol}://${location.host}/ws/{{room}}`);

const ctx = document.getElementById("chart").getContext("2d");

ws.onmessage = e => {
  const data = JSON.parse(e.data);

  document.getElementById("board").innerHTML = data.board;

  const prob = data.prob;
  document.getElementById("whiteBar").style.height = (prob*100)+"%";
  document.getElementById("blackBar").style.height = ((1-prob)*100)+"%";

  drawChart(data.evals);
  renderMoves(data.history);
};

function drawChart(evals){
  ctx.clearRect(0,0,400,150);

  ctx.beginPath();
  evals.forEach((v,i)=>{
    let y = 75 - v/10;
    if(i===0) ctx.moveTo(i*10,y);
    else ctx.lineTo(i*10,y);
  });
  ctx.stroke();
}

function renderMoves(history){
  let html = "<h3>Jogadas</h3>";
  history.forEach(h=>{
    html += `<div>${h.move} - ${h.label}</div>`;
  });
  document.getElementById("moves").innerHTML = html;
}

let selected = null;

document.addEventListener("click", e=>{
  if(e.target.dataset.square){
    if(!selected){
      selected = e.target.dataset.square;
    } else {
      ws.send(selected + e.target.dataset.square);
      selected = null;
    }
  }
});
</script>

</body>
</html>
HTML

echo "✅ Atualização concluída!"
echo "👉 Rode: uvicorn app.main:app --reload"
