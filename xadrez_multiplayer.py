import streamlit as st # Apenas se quiser manter compatibilidade, mas o foco aqui é FastAPI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import chess
import chess.svg
import json
import base64
import urllib.parse

app = FastAPI()

class ChessArena:
    def __init__(self):
        self.rooms = {}

    def get_initial_state(self):
        return {
            "fen": chess.Board().fen(),
            "p1": {"nome": None, "sid": None, "cor": "Brancas"},
            "p2": {"nome": None, "sid": None, "cor": "Pretas"},
            "turno": "w",
            "logs": ["Partida iniciada."],
            "vitoria": False,
            "vencedor": None
        }

    async def connect(self, websocket: WebSocket, room_id: str, name: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {"connections": [], "state": self.get_initial_state()}

        sid = str(id(websocket))
        state = self.rooms[room_id]["state"]

        # Atribuição inteligente de jogadores
        if not state["p1"]["sid"]:
            state["p1"].update({"nome": name, "sid": sid})
        elif not state["p2"]["sid"] and state["p1"]["sid"] != sid:
            state["p2"].update({"nome": name, "sid": sid})

        self.rooms[room_id]["connections"].append({"ws": websocket, "sid": sid, "name": name})
        return sid

    async def broadcast(self, room_id: str):
        if room_id not in self.rooms: return
        room = self.rooms[room_id]
        board = chess.Board(room["state"]["fen"])

        # Gera o SVG do tabuleiro
        svg_data = chess.svg.board(board=board, size=400)

        for conn in room["connections"]:
            data = {
                "state": room["state"],
                "board_svg": svg_data,
                "your_sid": conn["sid"],
                "is_full": True if (room["state"]["p1"]["sid"] and room["state"]["p2"]["sid"]) else False
            }
            try:
                await conn["ws"].send_text(json.dumps(data))
            except:
                pass

arena = ChessArena()

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Xadrez Arena</title>
            <style>
                body { background: #1a1a1a; color: #fff; font-family: sans-serif; text-align: center; padding: 50px 20px; }
                input { padding: 15px; margin: 10px; width: 90%; max-width: 300px; border-radius: 8px; border: none; font-size: 16px; }
                button { padding: 15px; width: 90%; max-width: 300px; background: #4CAF50; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; }
                button:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <h1>♟️ Xadrez Real-Time</h1>
            <input type="text" id="nome" placeholder="Seu Nome"><br>
            <input type="text" id="sala" placeholder="ID da Sala (ex: 123)"><br>
            <button onclick="entrar()">ENTRAR NA SALA</button>
            <script>
                function entrar() {
                    const n = document.getElementById('nome').value;
                    const s = document.getElementById('sala').value;
                    if(n && s) location.href = `/game/${s}?nome=${encodeURIComponent(n)}`;
                    else alert("Preencha seu nome e a sala!");
                }
            </script>
        </body>
    </html>
    """

@app.get("/game/{room_id}", response_class=HTMLResponse)
async def game_page(room_id: str, nome: str):
    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ background: #222; color: #eee; font-family: monospace; text-align: center; margin: 0; overflow-x: hidden; }}
                #board-container {{ margin: 10px auto; width: 350px; height: 350px; position: relative; cursor: pointer; border: 2px solid #444; }}
                #board-container svg {{ width: 100%; height: 100%; }}
                .overlay {{ position: absolute; top: 0; left: 0; display: grid; grid-template-columns: repeat(8, 1fr); grid-template-rows: repeat(8, 1fr); width: 100%; height: 100%; }}
                .square {{ border: 1px solid transparent; box-sizing: border-box; }}
                .selected {{ background: rgba(255, 255, 0, 0.4) !important; }}
                .status-bar {{ padding: 15px; font-weight: bold; background: #333; min-height: 20px; }}
                .info {{ font-size: 0.8em; color: #888; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="status-bar" id="status">Conectando...</div>
            <div id="board-container">
                <div id="svg-target"></div>
                <div class="overlay" id="click-grid"></div>
            </div>
            <div id="logs" class="info"></div>
            <div style="margin-top:20px;"><button onclick="location.href='/'" style="padding:10px; background:#444; color:#fff; border:none; border-radius:5px;">Sair da Sala</button></div>

            <script>
                let mySid = null;
                let selectedSquare = null;
                const squares = [
                    'a8','b8','c8','d8','e8','f8','g8','h8',
                    'a7','b7','c7','d7','e7','f7','g7','h7',
                    'a6','b6','c6','d6','e6','f6','g6','h6',
                    'a5','b5','c5','d5','e5','f5','g5','h5',
                    'a4','b4','c4','d4','e4','f4','g4','h4',
                    'a3','b3','c3','d3','e3','f3','g3','h3',
                    'a2','b2','c2','d2','e2','f2','g2','h2',
                    'a1','b1','c1','d1','e1','f1','g1','h1'
                ];
                
                const grid = document.getElementById('click-grid');
                squares.forEach(sq => {{
                    const div = document.createElement('div');
                    div.className = 'square';
                    div.id = 'sq-' + sq;
                    div.onclick = () => handleSquareClick(sq);
                    grid.appendChild(div);
                }});

                const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
                const host = location.host;
                const room = "{room_id}";
                const user = encodeURIComponent("{nome}");
                
                const socket = new WebSocket(`${{protocol}}://${{host}}/ws/${{room}}/${{user}}`);

                socket.onopen = () => {{
                    document.getElementById('status').innerText = "CONECTADO! AGUARDANDO...";
                }};

                socket.onmessage = function(e) {{
                    const data = JSON.parse(e.data);
                    if(!mySid) mySid = data.your_sid;
                    
                    document.getElementById('svg-target').innerHTML = data.board_svg;
                    
                    const state = data.state;
                    const isP1 = state.p1.sid === mySid;
                    const isP2 = state.p2.sid === mySid;
                    const meuTurno = (state.turno === 'w' && isP1) || (state.turno === 'b' && isP2);

                    const status = document.getElementById('status');
                    if(!data.is_full) {{
                        status.innerText = "AGUARDANDO OPONENTE...";
                        status.style.color = "#aaa";
                    }} else {{
                        status.innerText = meuTurno ? "SUA VEZ!" : "AGUARDE O OPONENTE";
                        status.style.color = meuTurno ? "#0f0" : "#f00";
                        document.getElementById('logs').innerText = `Você é as ${{isP1 ? "Brancas" : "Pretas"}}. Sala: ${{room}}`;
                    }}
                }};

                socket.onerror = () => {{
                    document.getElementById('status').innerText = "ERRO DE CONEXÃO!";
                }};

                function handleSquareClick(sq) {{
                    if(!selectedSquare) {{
                        selectedSquare = sq;
                        document.getElementById('sq-'+sq).classList.add('selected');
                    }} else {{
                        const move = selectedSquare + sq;
                        if(socket.readyState === WebSocket.OPEN) {{
                            socket.send(move);
                        }}
                        document.querySelectorAll('.square').forEach(s => s.classList.remove('selected'));
                        selectedSquare = null;
                    }}
                }}
            </script>
        </body>
    </html>
    """

@app.websocket("/ws/{room_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_name: str):
    # Decode do nome para evitar problemas com caracteres especiais
    name = urllib.parse.unquote(player_name)
    sid = await arena.connect(websocket, room_id, name)
    await arena.broadcast(room_id)
    
    try:
        while True:
            move_uci = await websocket.receive_text()
            room = arena.rooms[room_id]
            state = room["state"]
            board = chess.Board(state["fen"])

            is_p1 = state["p1"]["sid"] == sid
            is_p2 = state["p2"]["sid"] == sid
            meu_turno = (board.turn == chess.WHITE and is_p1) or (board.turn == chess.BLACK and is_p2)

            if meu_turno:
                try:
                    move = chess.Move.from_uci(move_uci.strip().lower())
                    if move in board.legal_moves:
                        board.push(move)
                        state["fen"] = board.fen()
                        state["turno"] = "w" if board.turn == chess.WHITE else "b"
                        await arena.broadcast(room_id)
                except:
                    pass
    except WebSocketDisconnect:
        # Limpeza ao desconectar
        room = arena.rooms[room_id]
        room["connections"] = [c for c in room["connections"] if c["sid"] != sid]
        if state["p1"]["sid"] == sid: state["p1"] = {"nome": None, "sid": None, "cor": "Brancas"}
        if state["p2"]["sid"] == sid: state["p2"] = {"nome": None, "sid": None, "cor": "Pretas"}
        await arena.broadcast(room_id)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
