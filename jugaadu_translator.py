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
CONTRIBUTIONS_FILE = "contributions_db.json"
AUDIO_DIR = "audio_contributions"

# --- OpenAI API Key Setup ---
# For security, it's recommended to use Streamlit's secrets management
# https://docs.streamlit.io/library/advanced-features/secrets-management
# For local development, you can set the environment variable.
openai.api_key = os.environ.get("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY"))

st.set_page_config(
    page_title="Jugaadu Translator",
    page_icon="💡",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Create directory for audio files if it doesn't exist ---
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

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
        # Save the audio bytes to a temporary file
        temp_audio_path = os.path.join(AUDIO_DIR, "temp_recording.wav")
        with open(temp_audio_path, "wb") as f:
            f.write(audio_bytes)
        
        with open(temp_audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        
        os.remove(temp_audio_path) # Clean up the temporary file
        return transcript['text']
    except Exception as e:
        st.error(f"Error in transcription: {e}")
        return None

def summarize_text_for_title_desc(text):
    """Generates a title and description for a text using OpenAI's GPT model."""
    if not openai.api_key:
        st.error("OpenAI API key is not set. Please configure it.")
        return None, None
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates a short, catchy title and a brief, one-sentence description for the given text."},
                {"role": "user", "content": f"Generate a title and a one-sentence description for the following text:\n\n{text}"}
            ]
        )
        summary = response.choices[0].message['content'].strip()
        # Simple parsing of the response
        parts = summary.split("\n")
        title = parts[0].replace("Title: ", "").strip()
        description = parts[1].replace("Description: ", "").strip() if len(parts) > 1 else ""
        return title, description
    except Exception as e:
        st.error(f"Error in summarization: {e}")
        return None, None

def text_to_speech(text):
    """Converts text to speech using gTTS and returns audio bytes."""
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

# --- Main Application ---

# Load the data at the start
phrases_db = load_database(DB_FILE)
contributions_db = load_database(CONTRIBUTIONS_FILE)

# --- UI Layout ---

st.title("💡 Jugaadu Local Phrase Translator")
st.markdown("""
A community-built translator to bridge communication gaps.
""")

# --- Sidebar for Mode Selection ---
st.sidebar.header("What do you want to do?")
app_mode = st.sidebar.radio(
    "Choose a mode:",
    ('Translate a Phrase', 'Contribute a New Phrase', 'Record and Contribute')
)

# --- Mode 1: Translation ---
if app_mode == 'Translate a Phrase':
    st.header("🔄 Translate")

    direction = st.radio(
        "Select translation direction:",
        ('Local Dialect → Standard English', 'Standard English → Local Dialect')
    )

    if direction == 'Local Dialect → Standard English':
        input_label = "Enter the local phrase you want to translate:"
        source_db = phrases_db
        not_found_message = "Sorry, I don't know that one yet! You can add it in the 'Contribute' mode."
    else: # English to Local
        input_label = "Enter the Standard English phrase you want to translate:"
        english_to_local_db = {v.lower(): k for k, v in phrases_db.items()}
        source_db = english_to_local_db
        not_found_message = "Sorry, no local equivalent found. Feel free to contribute one!"

    user_input = st.text_input(input_label, placeholder="Type a phrase here...")

    if st.button("Translate", use_container_width=True, type="primary"):
        if user_input:
            query = user_input.strip().lower()
            result = source_db.get(query, not_found_message)
            
            st.subheader("Translation:")
            st.success(f"**{result}**")

            if result != not_found_message:
                st.subheader("Listen to the Translation:")
                audio_bytes = text_to_speech(result)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")
        else:
            st.warning("Please enter a phrase to translate.")

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

# --- Mode 3: Record and Contribute ---
elif app_mode == 'Record and Contribute':
    st.header("🎤 Record a Phrase")
    st.info("Contribute by recording a phrase. We'll transcribe it and generate a title and description.", icon="🗣️")

    audio_bytes = audio_recorder(
        text="Click to Record",
        recording_color="#e8b62c",
        neutral_color="#6a6a6a",
        icon_name="microphone",
        pause_threshold=2.0,
    )

    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")

        if st.button("Process Recording", use_container_width=True, type="primary"):
            with st.spinner("Transcribing audio..."):
                transcribed_text = transcribe_audio(audio_bytes)

            if transcribed_text:
                st.subheader("Transcription:")
                st.write(transcribed_text)

                with st.spinner("Generating title and description..."):
                    title, description = summarize_text_for_title_desc(transcribed_text)

                if title and description:
                    st.subheader("Generated Title:")
                    st.write(title)
                    st.subheader("Generated Description:")
                    st.write(description)
                    
                    st.subheader("Get Geolocation")
                    location = streamlit_geolocation()
                    if location and location.get('latitude'):
                        st.success(f"Location captured: Latitude {location['latitude']}, Longitude {location['longitude']}")

                        if st.button("Save Contribution", use_container_width=True):
                            # Save the audio file
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            audio_filename = f"{timestamp}.wav"
                            audio_filepath = os.path.join(AUDIO_DIR, audio_filename)
                            with open(audio_filepath, "wb") as f:
                                f.write(audio_bytes)

                            # Save metadata
                            contribution_id = f"contribution_{len(contributions_db) + 1}"
                            contributions_db[contribution_id] = {
                                "title": title,
                                "description": description,
                                "transcribed_text": transcribed_text,
                                "geolocation": {
                                    "latitude": location['latitude'],
                                    "longitude": location['longitude']
                                },
                                "audio_file": audio_filepath,
                                "timestamp": timestamp
                            }
                            save_database(contributions_db, CONTRIBUTIONS_FILE)
                            st.success("Your contribution has been saved!")
                            st.balloons()
                    else:
                        st.warning("Could not retrieve location. Please allow location access in your browser.")
                else:
                    st.error("Could not generate a title and description.")
            else:
                st.error("Transcription failed.")

# --- Displaying the Raw Data (Optional) ---
with st.expander("🧐 See all known phrases (the current database)"):
    if phrases_db:
        st.json(phrases_db)
    else:
        st.write("The phrase database is currently empty. Contribute a phrase to get started!")

with st.expander("🎙️ See all voice contributions"):
    if contributions_db:
        st.json(contributions_db)
    else:
        st.write("The voice contribution database is currently empty. Record a contribution to get started!")
