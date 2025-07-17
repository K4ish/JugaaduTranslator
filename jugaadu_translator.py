# File: jugaadu_translator.py

import streamlit as st
import json
import os
import openai
from gtts import gTTS
from streamlit_geolocation import streamlit_geolocation
from audio_recorder_streamlit import audio_recorder
import datetime

# --- Configuration & Setup ---
DB_FILE = "phrases_db.json"
TRANSLATION_LOG_FILE = "translation_log.json"
TRANSLATION_AUDIO_DIR = "audio_translations" # For audio from the translate page

st.set_page_config(
    page_title="Jugaadu Translator",
    page_icon="💡",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- OpenAI API Key Setup ---
# Recommended: Use Streamlit's secrets management for deployment
# https://docs.streamlit.io/library/advanced-features/secrets-management
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))

# --- Create directories if they don't exist ---
os.makedirs(TRANSLATION_AUDIO_DIR, exist_ok=True)

# --- Initialize Session State ---
# This helps manage state between user interactions like recording and translating
if 'text_input' not in st.session_state:
    st.session_state.text_input = ""
if 'is_voice_input' not in st.session_state:
    st.session_state.is_voice_input = False
if 'audio_bytes' not in st.session_state:
    st.session_state.audio_bytes = None


# --- Data Handling Functions ---

def load_database(file_path):
    """Loads a database from a JSON file."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_database(data, file_path):
    """Saves updated data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- AI and Utility Functions ---

def transcribe_audio(audio_bytes):
    """Transcribes audio using OpenAI's Whisper model."""
    if not openai.api_key:
        st.error("OpenAI API key is not set. Please configure it.")
        return None
    try:
        temp_audio_path = os.path.join(TRANSLATION_AUDIO_DIR, "temp_recording.wav")
        with open(temp_audio_path, "wb") as f:
            f.write(audio_bytes)
        with open(temp_audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        os.remove(temp_audio_path)
        return transcript['text']
    except Exception as e:
        st.error(f"Error in transcription: {e}")
        return None

def generate_title_desc(text):
    """Generates a title and description for a text using OpenAI's GPT model."""
    if not openai.api_key:
        return "N/A", "N/A"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that creates a short title and a one-sentence description for the given text. Format it as 'Title: [Your Title]\\nDescription: [Your Description]'."},
                {"role": "user", "content": text}
            ]
        )
        summary = response.choices[0].message['content'].strip()
        parts = summary.split("\n")
        title = parts[0].replace("Title:", "").strip()
        description = parts[1].replace("Description:", "").strip() if len(parts) > 1 else ""
        return title, description
    except Exception:
        return "Summary Error", "Could not generate summary."

def text_to_speech(text):
    """Converts text to speech and returns audio bytes."""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        audio_fp = "temp_tts.mp3"
        tts.save(audio_fp)
        with open(audio_fp, 'rb') as f:
            audio_bytes = f.read()
        os.remove(audio_fp)
        return audio_bytes
    except Exception as e:
        st.error(f"Error in text-to-speech: {e}")
        return None

def log_voice_translation(audio_bytes, original_text, translated_text, geolocation):
    """Saves the audio file and logs the translation details."""
    st.info("Saving translation log with geolocation and audio...")

    log_db = load_database(TRANSLATION_LOG_FILE)
    
    # Generate metadata
    title, description = generate_title_desc(original_text)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_id = f"translation_{timestamp}"
    audio_filename = f"{log_id}.wav"
    audio_filepath = os.path.join(TRANSLATION_AUDIO_DIR, audio_filename)
    
    # Save the audio file
    with open(audio_filepath, "wb") as f:
        f.write(audio_bytes)
        
    # Create the log entry
    log_db[log_id] = {
        "title": title,
        "description": description,
        "original_transcription": original_text,
        "translated_text": translated_text,
        "geolocation": geolocation,
        "audio_file": audio_filepath,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Save the updated log database
    save_database(log_db, TRANSLATION_LOG_FILE)
    st.success("Translation log saved!")

# --- Main Application ---

phrases_db = load_database(DB_FILE)

st.title("💡 Jugaadu Local Phrase Translator")
st.markdown("A community-built translator to bridge communication gaps.")

st.sidebar.header("What do you want to do?")
app_mode = st.sidebar.radio(
    "Choose a mode:",
    ('Translate a Phrase', 'Contribute a New Phrase')
)

# --- Mode 1: Translation ---
if app_mode == 'Translate a Phrase':
    st.header("🔄 Translate")

    direction = st.radio(
        "Select translation direction:",
        ('Local Dialect → Standard English', 'Standard English → Local Dialect'),
        key="translation_direction"
    )

    # --- VOICE-TO-TEXT RECORDING ---
    st.markdown("##### Record your phrase:")
    audio_bytes = audio_recorder(
        text="", # No text label on the button
        icon_size="2x",
        pause_threshold=2.0,
    )
    
    if audio_bytes:
        with st.spinner("Transcribing your phrase..."):
            transcribed_text = transcribe_audio(audio_bytes)
            if transcribed_text:
                st.session_state.text_input = transcribed_text
                st.session_state.is_voice_input = True
                st.session_state.audio_bytes = audio_bytes
                st.success("Transcription complete. Press 'Translate' below.")
            else:
                st.error("Transcription failed. Please try again.")

    # --- TEXT INPUT AND TRANSLATION ---
    st.markdown("##### Or type it here:")
    user_input = st.text_input(
        "Enter phrase:",
        placeholder="Type or record a phrase...",
        key="text_input",
        label_visibility="collapsed"
    )

    if st.button("Translate", use_container_width=True, type="primary"):
        if st.session_state.text_input:
            query = st.session_state.text_input.strip().lower()

            if direction == 'Local Dialect → Standard English':
                source_db = phrases_db
                not_found_message = "Sorry, I don't know that one yet! You can add it in the 'Contribute' mode."
            else:
                english_to_local_db = {v.lower(): k for k, v in phrases_db.items()}
                source_db = english_to_local_db
                not_found_message = "Sorry, no local equivalent found. Feel free to contribute one!"

            result = source_db.get(query, not_found_message)
            
            st.subheader("Translation:")
            st.success(f"**{result}**")

            # Text-to-Speech for the result
            if result != not_found_message:
                tts_audio = text_to_speech(result)
                if tts_audio:
                    st.audio(tts_audio, format="audio/mp3")

            # --- GEOLOCATION AND STORAGE FOR VOICE INPUTS ---
            if st.session_state.get('is_voice_input', False) and result != not_found_message:
                st.subheader("📍 Geolocation & Storage")
                location = streamlit_geolocation()
                
                geo_data = {"latitude": None, "longitude": None}
                if location and location.get('latitude'):
                    geo_data['latitude'] = location['latitude']
                    geo_data['longitude'] = location['longitude']
                    st.write(f"Location captured: Lat {geo_data['latitude']}, Lon {geo_data['longitude']}")
                else:
                    st.warning("Could not retrieve location. Please allow location access in your browser to log it.")
                
                # Log the voice translation details
                log_voice_translation(
                    audio_bytes=st.session_state.audio_bytes,
                    original_text=query,
                    translated_text=result,
                    geolocation=geo_data
                )

            # Reset voice input flag after processing
            st.session_state.is_voice_input = False
            st.session_state.audio_bytes = None

        else:
            st.warning("Please enter or record a phrase to translate.")

# --- Mode 2: Crowdsourcing / Contribution ---
elif app_mode == 'Contribute a New Phrase':
    st.header("✍️ Add Your Own Phrase")
    st.info("Help us grow! Your contributions make the translator smarter for everyone.", icon="🙏")

    with st.form("contribution_form"):
        local_phrase = st.text_input("Enter the Local/Colloquial Phrase:")
        standard_english_phrase = st.text_input("Enter its Standard English Equivalent:")
        
        submitted = st.form_submit_button("Submit Contribution", use_container_width=True)

        if submitted:
            if local_phrase and standard_english_phrase:
                local_key = local_phrase.strip().lower()
                english_value = standard_english_phrase.strip()
                
                phrases_db[local_key] = english_value
                save_database(phrases_db, DB_FILE)
                
                st.success(f"Thank you! '{local_phrase}' has been added to the translator.")
                st.balloons()
            else:
                st.error("Please fill in both fields before submitting.")

# --- Displaying the Raw Data (Optional) ---
with st.expander("🧐 See all known phrases (the translation database)"):
    st.json(load_database(DB_FILE))

with st.expander("🎙️ See all voice translation logs"):
    st.json(load_database(TRANSLATION_LOG_FILE))
