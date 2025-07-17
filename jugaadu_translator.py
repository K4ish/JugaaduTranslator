import streamlit as st
import json
import os
import geocoder
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# File & Google Sheets config
DB_FILE = "phrases_db.json"
GSHEET_CREDS = "your_credentials.json"  # Replace with your JSON path
GSHEET_NAME = "Jugaadu_Translations"   # Replace with your Sheet name

# --- Google Sheets Helper ---
def append_to_gsheet(local, english, location):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GSHEET_CREDS, scope)
    client = gspread.authorize(creds)
    sheet = client.open(GSHEET_NAME).sheet1
    sheet.append_row([local, english, location])

# --- DB Load/Save ---
def load_database():
    if not os.path.exists(DB_FILE):
        initial = {
            "kaisa hai?": "How are you?",
            "sab theek hai": "Everything is fine.",
            "tuition laga lo": "Get a tutor / Start tuition classes.",
            "timepass kar raha hoon": "I'm just passing time.",
            "panga mat le": "Don't mess with me.",
            "oye!": "Hey!",
            "chalega": "It will work / That's acceptable."
        }
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial, f, ensure_ascii=False, indent=4)
        return initial
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_database(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- App Setup ---
st.set_page_config(page_title="Jugaadu Translator", page_icon="💡", layout="centered")
phrases_db = load_database()

# Sidebar
st.sidebar.header("What do you want to do?")
app_mode = st.sidebar.radio("Choose a mode:", ('Translate a Phrase', 'Contribute a New Phrase'))

# --- Translation Mode ---
if app_mode == 'Translate a Phrase':
    st.title("🔄 Translate")
    direction = st.radio(
        "Select translation direction:",
        ('Local Dialect → Standard English', 'Standard English → Local Dialect')
    )
    if direction.startswith('Local'):
        input_label = "Enter the local phrase to translate:"
        source_db = phrases_db
        not_found_message = "Sorry, I don't know that one yet! Add it in 'Contribute' mode."
    else:
        input_label = "Enter the Standard English phrase to translate:"
        english_to_local_db = {v.lower(): k for k, v in phrases_db.items()}
        source_db = english_to_local_db
        not_found_message = "Sorry, no local equivalent found. Feel free to contribute one!"
    user_input = st.text_input(input_label, placeholder="Type a phrase here...")

    if st.button("Translate", use_container_width=True, type="primary"):
        if user_input:
            result = source_db.get(user_input.strip().lower(), not_found_message)
            st.subheader("Translation:")
            st.success(f"**{result}**")
        else:
            st.warning("Please enter a phrase to translate.")

# --- Contribution Mode ---
else:
    st.title("✍️ Add Your Own Phrase")
    st.info("Help us grow! Your contributions make the translator smarter for everyone.", icon="🙏")

    # 1. Detect location via IP
    loc = geocoder.ip('me')
    user_location = f"{loc.city}, {loc.country}" if loc.city else "Unknown"

    # 2. Provide optional audio input
    st.subheader("🎤 Optional: Record your voice for input")
    audio_file = st.file_uploader("Upload an audio clip (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])
    transcript = ""
    if audio_file:
        st.audio(audio_file)
        audio = AudioSegment.from_file(audio_file).set_channels(1).set_frame_rate(16000)
        with BytesIO() as buf:
            audio.export(buf, format="wav")
            buf.seek(0)
            recog = sr.Recognizer()
            with sr.AudioFile(buf) as source:
                audio_data = recog.record(source)
                try:
                    transcript = recog.recognize_google(audio_data)
                    st.success(f"Recognized Text: {transcript}")
                except sr.UnknownValueError:
                    st.error("Could not understand the audio.")
                except sr.RequestError:
                    st.error("Speech recognition service error.")

    # Contribution form
    with st.form("contrib_form"):
        local_phrase = st.text_input("Enter the Local/Colloquial Phrase:", value=transcript)
        standard_english_phrase = st.text_input("Enter its Standard English Equivalent:")
        submitted = st.form_submit_button("Submit Contribution")

        if submitted:
            if local_phrase and standard_english_phrase:
                key = local_phrase.strip().lower()
                val = standard_english_phrase.strip()
                phrases_db[key] = val
                save_database(phrases_db)
                append_to_gsheet(key, val, user_location)
                st.success(f"Thank you! '{local_phrase}' has been added.")
                st.balloons()
            else:
                st.error("Please fill in both fields before submitting.")

# --- View Database ---
with st.expander("🧐 See all known phrases (the current database)"):
    st.json(phrases_db)
