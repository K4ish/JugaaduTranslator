# File: jugaadu_translator.py

import streamlit as st
import json
import os

# --- Configuration & Setup ---
DB_FILE = "phrases_db.json"

st.set_page_config(
    page_title="Jugaadu Translator",
    page_icon="💡",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Data Handling Functions (for offline storage) ---

def load_database():
    """Loads the phrase database from the JSON file."""
    if not os.path.exists(DB_FILE):
        # If the file doesn't exist, create it with some initial examples
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
        # If file is empty or corrupted, return an empty dictionary
        return {}


def save_database(data):
    """Saves the updated phrase database to the JSON file."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- Main Application ---

# Load the data at the start
phrases_db = load_database()

# --- UI Layout ---

st.title("💡 Jugaadu Local Phrase Translator")
st.markdown("""
A community-built translator to bridge communication gaps. 
Works entirely offline!
""")

# --- Sidebar for Mode Selection ---
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
        ('Local Dialect → Standard English', 'Standard English → Local Dialect')
    )

    if direction == 'Local Dialect → Standard English':
        input_label = "Enter the local phrase you want to translate:"
        # The keys of our database are the local phrases
        source_db = phrases_db
        not_found_message = "Sorry, I don't know that one yet! You can add it in the 'Contribute' mode."
    else: # English to Local
        input_label = "Enter the Standard English phrase you want to translate:"
        # We need to create a reverse dictionary for this direction
        english_to_local_db = {v.lower(): k for k, v in phrases_db.items()}
        source_db = english_to_local_db
        not_found_message = "Sorry, no local equivalent found. Feel free to contribute one!"

    user_input = st.text_input(input_label, placeholder="Type a phrase here...")

    if st.button("Translate", use_container_width=True, type="primary"):
        if user_input:
            # Standardize input for better matching
            query = user_input.strip().lower()
            
            # Find the translation
            result = source_db.get(query, not_found_message)
            
            st.subheader("Translation:")
            st.success(f"**{result}**")
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
                # Standardize inputs before saving
                local_key = local_phrase.strip().lower()
                english_value = standard_english_phrase.strip()
                
                # Update the database in memory
                phrases_db[local_key] = english_value
                
                # Save the updated database to the file
                save_database(phrases_db)
                
                st.success(f"Thank you! '{local_phrase}' has been added to the translator.")
                st.balloons()
            else:
                st.error("Please fill in both fields before submitting.")

# --- Displaying the Raw Data (Optional) ---
with st.expander("🧐 See all known phrases (the current database)"):
    if phrases_db:
        st.json(phrases_db)
    else:
        st.write("The database is currently empty. Contribute a phrase to get started!")
