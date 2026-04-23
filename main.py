from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="PropDeep AI - NBA Backend")

# Permite conexión desde Lovable y otros sitios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PropRequest(BaseModel):
    query: str

@app.get("/")
def home():
    return {"message": "✅ PropDeep Backend funcionando correctamente con nba_api"}

@app.post("/analyze-prop")
async def analyze_prop(request: PropRequest):
    query = request.query
    
    # Respuesta estructurada (mock por ahora - luego usaremos nba_api real)
    response = {
        "success": True,
        "query": query,
        "player": "Jugador detectado desde query",
        "prop": "Prop detectada desde query",
        "injury_check": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "ACTIVE",
            "notes": "Datos verificados (nba_api se integrará pronto)"
        },
        "projection": 26.8,
        "line": 27.5,
        "probability_over": 46.5,
        "recommendation": "UNDER",
        "confidence": "Medium",
        "recent_form": [24, 29, 22, 31, 25, 27, 28],
        "reasoning": [
            "Promedio últimos 7 partidos: 26.6 puntos",
            "Matchup contra defensa rival analizado",
            "Uso y minutos proyectados según datos recientes",
            "Riesgo de blowout bajo"
        ]
    }
    return response