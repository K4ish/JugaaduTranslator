# File: jugaadu_translator.py

import streamlit as st
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import speech_recognition as sr
import geocoder
from datetime import datetime

# --- Configuration & Setup ---
DB_FILE = "phrases_db.json"
CREDS_FILE = "google_sheets_creds.json"  # You'll need to create this file with your Google API credentials
SHEET_NAME = "Jugaadu_Translator_Phrases"  # Name of your Google Sheet

st.set_page_config(
    page_title="Jugaadu Translator",
    page_icon="💡",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Google Sheets Integration ---

def get_google_sheet():
    """Authenticates and returns the Google Sheet."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        return None

def sync_with_google_sheets(local_db):
    """Syncs the local database with Google Sheets."""
    sheet = get_google_sheet()
    if sheet:
        try:
            # Get all records from the sheet
            records = sheet.get_all_records()
            sheet_db = {row['Local Phrase'].lower(): row['English Translation'] for row in records}
            
            # Update local database with any new entries from the sheet
            updated = False
            for phrase, translation in sheet_db.items():
                if phrase not in local_db:
                    local_db[phrase] = translation
                    updated = True
            
            # If there were updates, save the local file
            if updated:
                save_database(local_db)
            
            return True
        except Exception as e:
            st.error(f"Error syncing with Google Sheets: {e}")
            return False
    return False

def add_to_google_sheets(local_phrase, english_phrase, location=None):
    """Adds a new phrase to Google Sheets."""
    sheet = get_google_sheet()
    if sheet:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            location_str = f"{location['lat']}, {location['lng']}" if location else "Unknown"
            sheet.append_row([local_phrase, english_phrase, timestamp, location_str])
            return True
        except Exception as e:
            st.error(f"Failed to add to Google Sheets: {e}")
            return False
    return False

# --- Location Services ---

def get_user_location():
    """Attempts to get the user's approximate location."""
    try:
        g = geocoder.ip('me')
        if g.ok:
            return {'lat': g.lat, 'lng': g.lng, 'city': g.city, 'country': g.country}
        return None
    except Exception as e:
        st.warning(f"Could not determine location: {e}")
        return None

# --- Speech Recognition ---

def recognize_speech():
    """Uses microphone input to recognize speech."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Speak now!")
        audio = r.listen(source)
    
    try:
        text = r.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        st.error("Could not understand audio")
        return None
    except sr.RequestError as e:
        st.error(f"Speech recognition error; {e}")
        return None

# --- Data Handling Functions ---

def load_database():
    """Loads the phrase database from the JSON file."""
    if not os.path.exists(DB_FILE):
        initial_data = {
            "kaisa hai?": "How are you?",
            "sab theek hai": "Everything is fine.",
            "tuition laga lo": "Get a tutor / Start tuition classes.",
            "timepass kar raha hoon": "I'm just passing time.",
            "panga mat le": "Don't mess with me.",
            "oye!": "Hey!",
            "chalega": "It will work / That's acceptable."
        }
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)
        return initial_data
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_database(data):
    """Saves the updated phrase database to the JSON file."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- Main Application ---

# Load the data at the start
phrases_db = load_database()

# Attempt to sync with Google Sheets on startup
if st.sidebar.checkbox("Enable Google Sheets Sync", True):
    if sync_with_google_sheets(phrases_db):
        st.sidebar.success("Synced with Google Sheets!")
    else:
        st.sidebar.warning("Using local database only")

# --- UI Layout ---

st.title("💡 Jugaadu Local Phrase Translator")
st.markdown("""
A community-built translator to bridge communication gaps. 
Now with voice input and cloud sync!
""")

# --- Sidebar for Mode Selection ---
st.sidebar.header("What do you want to do?")
app_mode = st.sidebar.radio(
    "Choose a mode:",
    ('Translate a Phrase', 'Contribute a New Phrase')
)

# --- Location Access ---
location_access = st.sidebar.checkbox("Share my location (helps improve regional translations)")
user_location = None
if location_access:
    user_location = get_user_location()
    if user_location:
        st.sidebar.success(f"Location: {user_location.get('city', 'Unknown')}, {user_location.get('country', 'Unknown')}")
    else:
        st.sidebar.warning("Could not determine location")

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

    # Voice Input Button
    if st.button("🎤 Use Voice Input", key="voice_input"):
        user_input = recognize_speech()
    else:
        user_input = ""

    text_input = st.text_input(input_label, value=user_input if user_input else "", placeholder="Type or speak a phrase here...")

    if st.button("Translate", use_container_width=True, type="primary"):
        if text_input:
            query = text_input.strip().lower()
            result = source_db.get(query, not_found_message)
            
            st.subheader("Translation:")
            st.success(f"**{result}**")
            
            # Log the translation request to Google Sheets
            if location_access and user_location:
                add_to_google_sheets(
                    text_input if direction == 'Local Dialect → Standard English' else result,
                    result if direction == 'Local Dialect → Standard English' else text_input,
                    user_location
                )
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
                
                # Update local database
                phrases_db[local_key] = english_value
                save_database(phrases_db)
                
                # Add to Google Sheets if enabled
                if location_access:
                    add_to_google_sheets(local_phrase, english_value, user_location)
                
                st.success(f"Thank you! '{local_phrase}' has been added to the translator.")
                st.balloons()
            else:
                st.error("Please fill in both fields before submitting.")

# --- Displaying the Raw Data ---
with st.expander("🧐 See all known phrases (the current database)"):
    if phrases_db:
        st.json(phrases_db)
    else:
        st.write("The database is currently empty. Contribute a phrase to get started!")

# --- Google Sheets Viewer ---
if st.sidebar.checkbox("Show Google Sheets Data", False):
    st.sidebar.info("This shows the data stored in Google Sheets")
    sheet = get_google_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            st.sidebar.write(f"Total entries in Google Sheets: {len(data)}")
            if data:
                st.sidebar.dataframe(data)
        except Exception as e:
            st.sidebar.error(f"Error reading Google Sheets: {e}")
