import os
import requests
from fastapi import FastAPI, Request
import google.generativeai as genai
from config import settings

app = FastAPI()

WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN
print(WHATSAPP_TOKEN)
PHONE_ID = settings.WHATSAPP_PHONE_NUMBER_ID
GEMINI_API_KEY = settings.GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


# ----------------------------------------
#  WEBHOOK VERIFICATION
# ----------------------------------------
@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == "verify123"
    ):
        return int(params.get("hub.challenge"))
    return "Verification token mismatch."


# ----------------------------------------
#  RECEIVE WHATSAPP MESSAGES
# ----------------------------------------
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        entry = data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages", [])
    except:
        return {"status": "ignored"}

    if not messages:
        return {"status": "no_messages"}

    msg = messages[0]
    sender = msg["from"]

    if msg["type"] == "audio":
        media_id = msg["audio"]["id"]
        filepath = download_media(media_id)

        summary = summarize_audio_with_gemini(filepath)

        send_text_message(sender, summary)

    return {"status": "processed"}


# ----------------------------------------
#  DOWNLOAD WHATSAPP AUDIO
# ----------------------------------------
def download_media(media_id):
    url = f"https://graph.facebook.com/v20.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    media_info = requests.get(url, headers=headers).json()
    media_url = media_info["url"]

    audio_file = requests.get(media_url, headers=headers)

    filename = "audio.ogg"
    with open(filename, "wb") as f:
        f.write(audio_file.content)

    return filename


# ----------------------------------------
#  USE GEMINI TO TRANSCRIBE + SUMMARIZE
# ----------------------------------------
def summarize_audio_with_gemini(filepath):
    with open(filepath, "rb") as f:
        audio_bytes = f.read()

    response = model.generate_content([
        "Transcribe the audio and then summarize it in 1–2 short sentences in hebrew. "
        "Your output should be the current date and time in this format - DD/MM/YYYY HH:MM, followed by the summary."
        "Exmple output: 25/12/2023 14:30 זהו סיכום ההקלטה.",
        {
            "mime_type": "audio/ogg",
            "data": audio_bytes
        }
    ])

    summary = response.text
    print("Gemini Summary:", summary)
    return summary


# ----------------------------------------
#  SEND MESSAGE BACK TO WHATSAPP
# ----------------------------------------
def send_text_message(to, text):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    requests.post(url, headers=headers, json=data)
