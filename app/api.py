import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .engine import ModerationEngine
import uvicorn
import os

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Add File Handler
fh = logging.FileHandler('backend.log')
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

app = FastAPI(title="ModeratorAI API")

# --- CORS SETUP ---
origins = [
    "http://localhost:3000",
    "http://localhost:8080",  # Spring Boot default
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "*" # Allow all for development/hackathon ease
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine instance
try:
    logger.info("Initializing Moderation Engine...")
    engine = ModerationEngine()
    logger.info("Moderation Engine initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Moderation Engine: {e}")
    engine = None

class Message(BaseModel):
    text: str

@app.get("/")
async def health_check():
    if engine:
        return {"status": "online", "message": "ModeratorAI is ready."}
    return {"status": "error", "message": "ModeratorAI engine failed to load."}

@app.post("/moderate")
async def moderate_endpoint(msg: Message):
    return await process_moderation(msg)

from fastapi import Request

@app.post("/api/chats/analyze-message")
async def moderate_endpoint_alias(request: Request):
    logger.info("Received request on alias endpoint /api/chats/analyze-message")
    try:
        body = await request.json()
        logger.info(f"DEBUG: Frontend sent body: {body}")
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    # Flexible field extraction
    text = body.get("text") or body.get("message") or body.get("content") or body.get("prompt")
    
    if not text:
        logger.error(f"Missing text field in body: {body}")
        raise HTTPException(status_code=422, detail="Missing 'text', 'message', or 'content' field in JSON")

    # Create Message object manually
    msg = Message(text=text)
    return await process_moderation(msg)

async def process_moderation(msg: Message):
    if not engine:
        raise HTTPException(status_code=503, detail="Moderation engine not available")
    
    logger.info(f"Received request: {msg.text[:50]}...")
    try:
        result = engine.moderate(msg.text)
        logger.info(f"Processed request. Toxic: {result['toxic']}")
        response_data = {
            "is_flagged": result["toxic"],
            "toxicity": result["toxic"],
            "is_toxic": result["toxic"],
            "severity_level": result["severity"],
            "severity": result["severity"],
            "level": result["severity"],
            "suggested_alternative": result["suggestion"],
            "suggestion": result["suggestion"],
            "original_text": msg.text
        }
        logger.info(f"DEBUG: Sending response: {response_data}")
        return response_data
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Check if port is available or handle gracefully is hard in script, 
    # but logging helps user debug.
    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)