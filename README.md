# ModeratorAI

A toxicity detection and detoxification system using ensemble deep learning models.

## Directory Structure

- `app/`: Core application code.
  - `api.py`: FastAPI backend entry point.
  - `engine.py`: Logic for toxicity detection and rewriting.
  - `dashboard.py`: Streamlit/Gradio dashboard.
- `models/`: Pre-trained and fine-tuned model weights.
- `scripts/`: Training scripts (`bartTraining.py`, `ensembleTraining.py`).
- `tests/`: Unit and integration tests.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the API:
   ```bash
   python -m app.api
   ```
   or
   ```bash
   uvicorn app.api:app --reload
   ```

3. Run the Dashboard:
   ```bash
   python app/dashboard.py
   ```

## API Endpoints

- `POST /moderate`: Analyze text for toxicity.
- `GET /`: Health check.
