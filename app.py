import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import (
    MAX_HISTORY,
    MAX_MESSAGE_LENGTH,
    MODEL_NAME,
    SYSTEM_PROMPT,
    TEMPERATURE,
)

load_dotenv()

app = Flask(__name__)


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")
    return genai.Client(api_key=api_key)


def build_contents(messages):
    contents = []
    for item in messages[-MAX_HISTORY:]:
        role = "user" if item.get("role") == "user" else "model"
        text = str(item.get("text", "")).strip()[:MAX_MESSAGE_LENGTH]
        if text:
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
    while contents and contents[0].role == "model":
        contents.pop(0)
    return contents


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    contents = build_contents(payload.get("messages", []))

    if not contents or contents[-1].role != "user":
        return jsonify({"error": "Send a message to get started."}), 400

    try:
        response = get_client().models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=TEMPERATURE,
            ),
        )
        reply = (response.text or "").strip()
        if not reply:
            return jsonify({"error": "No reply came back. Try rephrasing your tasks."}), 502
        return jsonify({"reply": reply})
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500
    except Exception:
        return jsonify({"error": "TaskPilot could not reach Gemini. Please try again."}), 502


if __name__ == "__main__":
    app.run(debug=True)
