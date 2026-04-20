import os
import urllib.parse
import json
import chess
import chess.svg
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

class ChessArena:
    def __init__(self):
        self.rooms = {}

    def get_initial_state(self):
        return {
            "fen": chess.Board().fen(),
            "p1": {"nome": None, "sid": None},
            "p2": {"nome": None, "sid": None},
            "turno": "w",
            "vitoria": False
        }

    async def connect(self, websocket: WebSocket, room_id: str, name: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {"connections": [], "state": self.get_initial_state()}

        room = self.rooms[room_id]
        
        # REGRA: Bloqueia se o nome já estiver na sala
        if any(conn["name"] == name for conn in room["connections"]):
            await websocket.send_text(json.dumps({"error": "Você já está nesta sala em outra aba!"}))
            await websocket.close()
            return None

        sid = str(id(websocket))
        state = room["state"]

        if not state["p1"]["sid"]:
            state["p1"].update({"nome": name, "sid": sid})
        elif not state["p2"]["sid"]:
            state["p2"].update({"nome": name, "sid": sid})

        room["connections"].append({"ws": websocket, "sid": sid, "name": name})
        return sid

    async def broadcast(self, room_id: str):
        if room_id not in self.rooms: return
        room = self.rooms[room_id]
        board = chess.Board(room["state"]["fen"])
        svg_data = chess.svg.board(board=board, size=400)

        for conn in room["connections"]:
            data = {
                "state": room["state"],
                "board_svg": svg_data,
                "your_sid": conn["sid"],
                "is_full": bool(room["state"]["p1"]["sid"] and room["state"]["p2"]["sid"])
            }
            try:
                await conn["ws"].send_text(json.dumps(data))
            except: pass

arena = ChessArena()

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { background: #1a1a1a; color: #fff; font-family: sans-serif; text-align: center; padding: 50px 20px; }
                input { padding: 15px; margin: 10px; width: 100%; max-width: 300px; border-radius: 8px; border: none; font-size: 16px; }
                button { padding: 15px; width: 100%; max-width: 300px; background: #4CAF50; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>♟️ Xadrez Real-Time</h1>
            <input type="text" id="nome" placeholder="Seu Nome"><br>
            <input type="text" id="sala" placeholder="ID da Sala"><br>
            <button onclick="entrar()">JOGAR</button>
            <script>
                function entrar() {
                    const n = document.getElementById('nome').value;
                    const s = document.getElementById('sala').value;
                    if(n && s) location.href = `/game/${s}?nome=${encodeURIComponent(n)}`;
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
                body {{ background: #222; color: #eee; font-family: sans-serif; text-align: center; margin: 0; }}
                .header-game {{ display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #333; }}
                .players-info {{ display: flex; gap: 10px; }}
                .player-box {{ padding: 5px 10px; border-radius: 4px; font-size: 12px; border: 1px solid #555; }}
                .active-turn {{ background: #4CAF50; color: white; border-color: #4CAF50; }}
                .btn-sair {{ background: #f44336; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; }}
                #board-container {{ margin: 20px auto; width: 340px; height: 340px; position: relative; border: 2px solid #555; }}
                #board-container svg {{ width: 100%; height: 100%; }}
                .overlay {{ position: absolute; top: 0; left: 0; display: grid; grid-template-columns: repeat(8, 1fr); grid-template-rows: repeat(8, 1fr); width: 100%; height: 100%; z-index: 10; }}
                .square {{ cursor: pointer; }}
                .selected {{ background: rgba(255, 255, 0, 0.4) !important; }}
                .status-bar {{ padding: 15px; font-weight: bold; background: #444; }}
            </style>
        </head>
        <body>
            <div class="header-game">
                <div class="players-info">
                    <div id="p1-display" class="player-box">⚪ ...</div>
                    <div id="p2-display" class="player-box">⚫ ...</div>
                </div>
                <button class="btn-sair" onclick="location.href='/'">SAIR</button>
            </div>
            <div class="status-bar" id="status">Conectando...</div>
            
            <div id="board-container">
                <div id="svg-target"></div>
                <div class="overlay" id="click-grid"></div>
            </div>

            <script>
                let mySid = null;
                let selectedSquare = null;
                const squares = ['a8','b8','c8','d8','e8','f8','g8','h8','a7','b7','c7','d7','e7','f7','g7','h7','a6','b6','c6','d6','e6','f6','g6','h6','a5','b5','c5','d5','e5','f5','g5','h5','a4','b4','c4','d4','e4','f4','g4','h4','a3','b3','c3','d3','e3','f3','g3','h3','a2','b2','c2','d2','e2','f2','g2','h2','a1','b1','c1','d1','e1','f1','g1','h1'];
                
                const grid = document.getElementById('click-grid');
                squares.forEach(sq => {{
                    const div = document.createElement('div');
                    div.className = 'square';
                    div.id = 'sq-' + sq;
                    div.onclick = () => handleSquareClick(sq);
                    grid.appendChild(div);
                }});

                const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
                const socket = new WebSocket(`${{protocol}}://${{location.host}}/ws/{room_id}/${{encodeURIComponent('{nome}')}}`);

                socket.onmessage = function(e) {{
                    const data = JSON.parse(e.data);
                    
                    if(data.error) {{
                        alert(data.error);
                        location.href = '/';
                        return;
                    }}

                    if(!mySid) mySid = data.your_sid;
                    document.getElementById('svg-target').innerHTML = data.board_svg;
                    
                    const state = data.state;
                    const isP1 = state.p1.sid === mySid;
                    const isP2 = state.p2.sid === mySid;
                    const meuTurno = (state.turno === 'w' && isP1) || (state.turno === 'b' && isP2);

                    document.getElementById('p1-display').innerText = "⚪ " + (state.p1.nome || "Aguardando...");
                    document.getElementById('p2-display').innerText = "⚫ " + (state.p2.nome || "Aguardando...");
                    document.getElementById('p1-display').className = "player-box " + (state.turno === 'w' ? "active-turn" : "");
                    document.getElementById('p2-display').className = "player-box " + (state.turno === 'b' ? "active-turn" : "");

                    const status = document.getElementById('status');
                    if(!data.is_full) {{
                        status.innerText = "AGUARDANDO OPONENTE...";
                    }} else {{
                        status.innerText = meuTurno ? "SUA VEZ!" : "VEZ DO OPONENTE";
                        status.style.color = meuTurno ? "#0f0" : "#ff4444";
                    }}
                }};

                function handleSquareClick(sq) {{
                    if(!selectedSquare) {{
                        selectedSquare = sq;
                        document.getElementById('sq-'+sq).classList.add('selected');
                    }} else {{
                        const move = selectedSquare + sq;
                        if(socket.readyState === 1) socket.send(move);
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
    name = urllib.parse.unquote(player_name)
    sid = await arena.connect(websocket, room_id, name)
    if not sid: return # Encerra se houver erro de duplicata

    await arena.broadcast(room_id)
    try:
        while True:
            move_uci = await websocket.receive_text()
            room = arena.rooms[room_id]
            state = room["state"]
            board = chess.Board(state["fen"])
            
            is_p1, is_p2 = state["p1"]["sid"] == sid, state["p2"]["sid"] == sid
            meu_turno = (board.turn == chess.WHITE and is_p1) or (board.turn == chess.BLACK and is_p2)

            if meu_turno:
                try:
                    move = chess.Move.from_uci(move_uci.strip().lower())
                    if move in board.legal_moves:
                        board.push(move)
                        state["fen"] = board.fen()
                        state["turno"] = "w" if board.turn == chess.WHITE else "b"
                        await arena.broadcast(room_id)
                except: pass
    except WebSocketDisconnect:
        # Ao desconectar, remove o SID do estado para permitir nova entrada
        room = arena.rooms.get(room_id)
        if room:
            state = room["state"]
            if state["p1"]["sid"] == sid: state["p1"].update({"nome": None, "sid": None})
            if state["p2"]["sid"] == sid: state["p2"].update({"nome": None, "sid": None})
            # Remove a conexão da lista
            room["connections"] = [c for c in room["connections"] if c["sid"] != sid]
            await arena.broadcast(room_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
