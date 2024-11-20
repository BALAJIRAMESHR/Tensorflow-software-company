import streamlit as st
import google.generativeai as genai
from googletrans import Translator
import threading
from streamlit_chat import message
import speech_recognition as sr
import time
import os
from gtts import gTTS
from playsound import playsound
import io
import re

# Directory to store voice files
VOICE_DIR = "data/voice/"
if not os.path.exists(VOICE_DIR):
    os.makedirs(VOICE_DIR)

# Language options
LANGUAGE_OPTIONS = {
    "English": "en",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Hindi": "hi",
}

# Initialize Generative AI and translator
translator = Translator()
genai.configure(api_key="YOUR-API-KEY")
model = genai.GenerativeModel("gemini-pro")


def text_to_audio(text, filename):
    """
    Converts bot's text response into an audio file using gTTS.
    """
    try:
        clean_text = re.sub(r"(\*{1,2}|_+|~+|`+)", "", text)  # Clean Markdown
        tts = gTTS(
            clean_text, lang=st.session_state.language
        )  # Language based on user choice
        file_path = os.path.join(VOICE_DIR, filename)
        tts.save(file_path)
        return file_path
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None


def play_audio(file_path):
    """
    Plays the generated audio file asynchronously.
    """
    if os.path.exists(file_path):
        try:
            threading.Thread(target=playsound, args=(file_path,)).start()
        except Exception as e:
            st.error(f"Error playing audio: {e}")
    else:
        st.warning("Audio file not found!")


def audio_to_text(audio_binary):
    recognizer = sr.Recognizer()
    try:
        # Convert binary audio to file-like object
        audio_file = io.BytesIO(audio_binary)
        with sr.AudioFile(audio_file) as source:
            print("Recording detected, processing...")
            audio_data = recognizer.record(source)
        # Perform speech-to-text conversion
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        return "Could not understand the audio."
    except sr.RequestError:
        return "Could not process audio due to a service issue."
    except Exception as e:
        return f"Unexpected error: {e}"


def record_audio():
    """
    Records audio from the microphone. Returns the audio object.
    """
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Adjusting for background noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Recording. Speak now!")
            audio = recognizer.listen(source)
            print("Recording complete.")
            return audio
    except Exception as e:
        print(f"Error during recording: {e}")
        return None


# Session state initialization function
def init_session_state():
    session_vars = {
        "user_name": "",
        "bot_name": "",
        "language": "en",
        "messages": [],
        "chat": model.start_chat(history=[]),
        "voice_id": 1,
        "speech_rate": 190,
        "speech_volume": 1.0,
        "listening": False,
    }

    for var, default in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default


# Conversation handling function
def handle_conversation(user_input):
    try:
        # Thinking placeholder
        thinking_placeholder = st.empty()
        thinking_placeholder.info("🤔 Thinking...")

        # Send message to AI
        response = st.session_state.chat.send_message(user_input)
        response_text = response.text

        # Truncate long responses
        lines = response_text.split("\n")
        truncated_response = "\n".join(lines[:10])

        # Clear thinking indicator
        thinking_placeholder.empty()

        # Append to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "bot", "content": truncated_response})

        # Convert bot's response to audio
        timestamp = str(int(time.time()))
        audio_filename = f"response_{timestamp}.mp3"
        audio_path = text_to_audio(truncated_response, audio_filename)

        # Play audio response
        if audio_path:
            play_audio(audio_path)

        return truncated_response

    except Exception as e:
        error_message = f"Sorry, I couldn't process your request. Error: {e}"
        st.session_state.messages.append({"role": "bot", "content": error_message})

        # Generate and play error audio
        timestamp = str(int(time.time()))
        audio_filename = f"error_{timestamp}.mp3"
        audio_path = text_to_audio(error_message, audio_filename)
        if audio_path:
            play_audio(audio_path)

        return None


def chat_page():
    init_session_state()

    st.title(f"Bot {st.session_state.bot_name}")

    # Chat history
    for msg in st.session_state.messages:
        message(msg["content"], is_user=(msg["role"] == "user"))

    # Voice input button
    if st.button("🎤 Start Voice Input"):
        # Record audio
        audio = record_audio()

        if audio:
            # Convert audio to text
            user_input = audio_to_text(audio.get_wav_data())

            # Show what was heard
            st.write(f"You said: {user_input}")

            # Process conversation and get response
            bot_response = handle_conversation(user_input)

            if bot_response:
                st.write(f"{st.session_state.bot_name} responded: {bot_response}")


def main():
    # Remove default padding
    st.markdown(
        """
    <style>
    .reportview-container .main .block-container{
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Always display chat page
    chat_page()


# Run the app
if __name__ == "__main__":
    main()
