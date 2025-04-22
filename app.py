from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import datetime
import time
import threading
import speech_recognition as sr
from gtts import gTTS
import os

app = Flask(__name__)
CORS(app)

# Shared state
alarms = []
tasks = []
listening_for_task = False

# Alarm thread
def check_alarms():
    while True:
        current_time = datetime.datetime.now().strftime("%H:%M")
        for alarm in alarms.copy():
            if alarm["time"] == current_time:
                alarms.remove(alarm)
                text_to_speech(f"Alarm! {alarm['message']}")
        time.sleep(10)

# Initialize alarm thread
alarm_thread = threading.Thread(target=check_alarms, daemon=True)
alarm_thread.start()

def text_to_speech(text):
    tts = gTTS(text=text, lang='en')
    filename = f"response_{int(time.time())}.mp3"
    tts.save(filename)
    return filename

def speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio).lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_command():
    audio_file = request.files['audio']
    command = speech_to_text(audio_file)
    
    if "time" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return jsonify({"response": f"The current time is {current_time}"})
    
    elif "date" in command:
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        return jsonify({"response": f"Today's date is {current_date}"})
    
    # Add other command handling here
    
    return jsonify({"response": "Command not recognized"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)