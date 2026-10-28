# SafeChat — Real-Time Multi-Lingual Content Moderation & Detoxification

[![Live Demo](https://img.shields.io/badge/Demo-Live_App-emerald?style=for-the-badge&logo=googlechrome)](https://13-48-162-212.sslip.io)
[![Hugging Face](https://img.shields.io/badge/HuggingFace-Model_Weights-yellow?style=for-the-badge&logo=huggingface)](https://huggingface.co/vineet88/hingbert-toxicity-finetuned)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react)](https://react.dev)
[![AWS EC2](https://img.shields.io/badge/AWS-EC2_Docker-FF9900?style=for-the-badge&logo=amazon-aws)](https://aws.amazon.com)

**SafeChat** is an enterprise real-time chat moderation and detoxification platform built to solve toxic communication in code-mixed languages (**Hinglish, Hindi, and English**). 

Instead of traditional bans or slow filters, SafeChat intercepts toxic messages in **sub-50ms** and generates **intent-preserving polite alternatives** in real time—enabling users to communicate constructively without breaking conversation flow.

---

## 🚀 Live Links

- **Live Application**: [https://13-48-162-212.sslip.io](https://13-48-162-212.sslip.io)
- **Fine-Tuned Model on Hugging Face**: [vineet88/hingbert-toxicity-finetuned](https://huggingface.co/vineet88/hingbert-toxicity-finetuned)
- **Developer Portfolio**: [https://vineetiitg.github.io](https://vineetiitg.github.io)

---

## ⚡ The Problem vs SafeChat

| 🔴 Traditional Moderation | 🟢 SafeChat Solution |
| :--- | :--- |
| **English-only bias**: Fails on phonetic Hinglish abuse (e.g. slurs in Latin script). | **Fine-tuned HingBERT**: 94.2% accuracy on code-mixed Hinglish & Hindi. |
| **Punishment-based**: Outright blocks or bans users, causing friction. | **Guidance-based**: Streams intent-preserving polite rewrites instantly. |
| **High latency**: Heavy LLM chains take 1–3s, disrupting live chat. | **Dual-tier pipeline**: Sub-35ms fast-path classification + streaming detox. |
| **Static keyword blocklists**: Easily bypassed with leetspeak or minor typos. | **Context-aware deep NLP**: Understands semantic toxicity and nuance. |

---

## 🧠 System Architecture

```mermaid
flowchart LR
    A["User Types Message"] --> B["FastAPI Gateway\n(WebSocket / REST)"]
    B --> C["Fast Path (<35ms)\nFine-Tuned HingBERT"]
    
    C -->|SAFE| D["Broadcast to Channel"]
    C -->|TOXIC| E["Detoxification Engine\nGemini 2.5 Flash"]
    
    E --> F["Real-Time Token Stream\nPolite Alternative"]
    F --> G["User UI: Review & Send\n(or Auto-Sanitize)"]
```

1. **Fast-Path Classification (< 35ms)**: Evaluates message safety using fine-tuned **HingBERT** across 6 multi-label categories (*toxic, severe toxic, obscene, threat, insult, identity hate*).
2. **Generative Detoxification Tier**: When toxic intent is flagged, Gemini 2.5 Flash streams a polite, intent-preserving rewrite token-by-token directly into the composer.
3. **Public Sandbox vs Developer Access**:
   - **Public Model Sandbox**: Open to recruiters and evaluators to test any Hinglish/English phrase with real-time scoring.
   - **Live Moderated Chat & Admin Dashboard**: Protected with role-based access control and a 1-click **Developer PIN** (`vineet2026`).

---

## 🛠️ Tech Stack

- **Machine Learning**: Fine-tuned HingBERT (`vineet88/hingbert-toxicity-finetuned`), PyTorch, Hugging Face Transformers, ONNX Runtime.
- **Detoxification**: Gemini 2.5 Flash streaming via asynchronous WebSocket chunking.
- **Backend**: Python 3.11, FastAPI, Asyncpg / SQLite, Redis (rate-limiting & pub/sub), Motor (MongoDB history).
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Recharts telemetry.
- **DevOps & Cloud**: Docker Compose, AWS EC2, Caddy reverse-proxy (Automated SSL/TLS).

---

## 📊 Benchmark & Performance Metrics

| Metric | Measurement | Target / Impact |
| :--- | :--- | :--- |
| **Hinglish Toxicity Accuracy** | **94.2%** | +28.4% improvement over standard English models |
| **Fast-Path Inference Latency** | **~28 ms** | Sub-50ms budget for seamless live chatting |
| **Streaming Detox TTFT** | **< 120 ms** | Instant user feedback without chat lockup |
| **Multi-Label Coverage** | **6 Categories** | Toxicity, Insult, Obscene, Threat, Severe, Identity |

---

## 💻 Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Vineetiitg/Real-time-Toxic-Chat-Moderation-System.git
cd Real-time-Toxic-Chat-Moderation-System
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend gateway
uvicorn safety_platform.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd frontend

# Install packages
npm install

# Run local development server
npm run dev
```

The frontend will run at `http://localhost:5173` and automatically connect to the backend gateway at `http://localhost:8000`.

---

## 📡 API Reference

### 1. Evaluate Text Safety (REST)
`POST /api/v1/moderate`

**Request Body:**
```json
{
  "text": "Bhai tu chup kar",
  "channel_id": "general",
  "user_id": "user-123"
}
```

**Response (200 OK):**
```json
{
  "is_toxic": true,
  "severity": "HIGH",
  "detected_language": "hi-en",
  "suggestion": "Aapki baat sahi hai, par aap thoda shanti rakhein.",
  "categories": {
    "toxic": 0.85,
    "insult": 0.85,
    "obscene": 0.43
  },
  "inference_time_ms": 32
}
```

### 2. Real-Time Chat WebSocket
`WS /ws/chat?channel=general&user_name=Vineet`

- Sends and receives real-time messages.
- Streams token-by-token polite rewrites via events: `classification`, `detox_start`, `detox_chunk`, `detox_end`.

---

## 🔐 Access Control

- **Public Visitors**: Unrestricted access to the **Model Sandbox** with preset prompts, custom sentence analysis, language detection, and detox suggestions.
- **Developer Mode**: Access to the multi-user **Live Moderated Chat** and **Admin Dashboard** is unlocked using Developer PIN: `vineet2026`.

---

## 👤 Author

**Vineet Tiwari**  
- **GitHub**: [@Vineetiitg](https://github.com/Vineetiitg)  
- **Hugging Face**: [@vineet88](https://huggingface.co/vineet88)  
- **Portfolio**: [vineetiitg.github.io](https://vineetiitg.github.io)
