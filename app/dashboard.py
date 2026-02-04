import gradio as gr
import requests

# Link to your running main.py (FastAPI)
API_URL = "http://127.0.0.1:8000/moderate"


def process_message(input_text):
    if not input_text.strip():
        return "⚠️ Please enter text", "N/A", "N/A"

    try:
        # Call the FastAPI service instead of the Engine directly
        response = requests.post(API_URL, json={"text": input_text})
        res = response.json()

        status = "⚠️ TOXIC" if res['is_flagged'] else "✅ SAFE"
        severity_map = ["Safe", "Low", "Medium", "High"]

        return status, severity_map[res['severity_level']], res['suggested_alternative']

    except Exception as e:
        return f"❌ Connection Error: {str(e)}", "Is main.py running?", "N/A"


demo = gr.Interface(
    fn=process_message,
    inputs=gr.Textbox(placeholder="Enter a message..."),
    outputs=[
        gr.Label(label="Safety Status"),
        gr.Text(label="Severity"),
        gr.Text(label="Detoxified Suggestion")
    ],
    title="GuardianAI Chat Moderator",
    description="Interface connecting to the FastAPI Backend."
)

if __name__ == "__main__":
    # Use a different port for the dashboard
    demo.launch(server_port=7860)