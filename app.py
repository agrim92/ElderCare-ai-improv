from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import datetime
import time
import threading
from threading import Lock
import speech_recognition as sr
from gtts import gTTS
import os

app = Flask(__name__)
CORS(app)

# Configure static folder
app.static_folder = 'static'
os.makedirs(os.path.join(app.static_folder, 'audio'), exist_ok=True)

# Shared state with thread safety
alarms = []
alarms_lock = Lock()
tasks = []
tasks_lock = Lock()

def handle_command(command):
    command = command.lower()
    
    # Time command
    if "time" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}"
    
    # Date command
    if "date" in command:
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        return f"Today's date is {current_date}"
    
    # Alarm commands
    if "set alarm" in command:
        try:
            time_str = command.split("for")[1].strip()
            with alarms_lock:
                alarms.append({"time": time_str, "message": "Your alarm is ringing!"})
            return f"Alarm set for {time_str}"
        except:
            return "Could not set alarm. Please specify time."
    
    return "Command not recognized"

def text_to_speech(text):
    tts = gTTS(text=text, lang='en')
    static_audio_dir = os.path.join(app.static_folder, 'audio')
    filename = f"response_{int(time.time())}.mp3"
    filepath = os.path.join(static_audio_dir, filename)
    tts.save(filepath)
    return f"/static/audio/{filename}"

def speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
            return recognizer.recognize_google(audio).lower()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"API request failed: {e}")
        return None
    except Exception as e:
        print(f"Error processing audio: {e}")
        return None

def check_alarms():
    while True:
        with alarms_lock:
            current_time = datetime.datetime.now().strftime("%H:%M")
            for alarm in alarms.copy():
                if alarm["time"] == current_time:
                    alarms.remove(alarm)
                    text_to_speech(f"Alarm! {alarm['message']}")
        time.sleep(1)

def cleanup_old_audio():
    while True:
        now = time.time()
        static_audio_dir = os.path.join(app.static_folder, 'audio')
        for filename in os.listdir(static_audio_dir):
            filepath = os.path.join(static_audio_dir, filename)
            if os.path.splitext(filename)[1] != '.mp3':
                continue
            if os.stat(filepath).st_mtime < now - 3600:
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error removing file {filename}: {e}")
        time.sleep(3600)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'wav', 'mp3'}

# Initialize background threads
threading.Thread(target=check_alarms, daemon=True).start()
threading.Thread(target=cleanup_old_audio, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-audio', methods=['POST'])
def handle_audio_command():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file received"}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '' or not allowed_file(audio_file.filename):
            return jsonify({"error": "Invalid audio file"}), 400
            
        command = speech_to_text(audio_file)
        if not command:
            return jsonify({"response": "Could not understand audio"})
            
        response = handle_command(command)
        return jsonify({
            "response": response,
            "audio": text_to_speech(response)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
