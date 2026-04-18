# ♟️ Xadrez Multi-Player Real-Time com Análise de Dados

Este projeto é uma plataforma de xadrez multiplayer que utiliza **FastAPI** e **WebSockets** para comunicação em tempo real, integrando o motor de análise **Stockfish** para fornecer métricas de desempenho e probabilidade de vitória durante a partida.

## 🚀 Funcionalidades
* **Multiplayer em Tempo Real:** Conexão instantânea via WebSockets.
* **Análise Preditiva:** Integração com Stockfish para avaliar a posição atual.
* **Visualização de Dados:** Barra de vantagem dinâmica e gráfico de evolução da partida (Série Temporal).
* **Classificação de Jogadas:** Identificação automática de "Boas jogadas", "Erros" e "Blunders".
* **Arquitetura Escalável:** Pronto para deploy em ambientes Cloud (como Render/Docker).

## 🧬 Ciência por trás do Projeto
Diferente de sistemas simples, este projeto aplica conceitos de **Data Science**:
* **Função Sigmoide:** Os valores de *Centipawns* do motor são convertidos em probabilidades reais de vitória através de uma curva logística:
  $$P(vitoria) = \frac{1}{1 + e^{-cp / 300}}$$
* **Análise de Variância:** O sistema monitora a flutuação da vantagem para classificar a qualidade técnica dos jogadores.

## 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python 3.11+
* **Framework:** FastAPI / Uvicorn
* **Lógica de Xadrez:** python-chess
* **Engine de IA:** Stockfish
* **Frontend:** HTML5, CSS3 (Flexbox/Grid), JavaScript (Canvas API)

## 📦 Como rodar o projeto
1. Instale as dependências: `pip install -r requirements.txt`
2. Certifique-se de ter o Stockfish instalado no sistema.
3. Inicie o servidor: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
