from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
import threading

app = Flask(__name__)
app.secret_key = "droproom-secret"
UPLOAD_FOLDER = 'uploads'
ROOMS = {}  # room_id: {"password": ..., "expires": ..., "files": [...]}
TTL_MINUTES = 30

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def cleanup_expired_rooms():
    while True:
        now = datetime.now()
        expired = [room_id for room_id, data in ROOMS.items() if now > data['expires']]
        for room_id in expired:
            for file in ROOMS[room_id]['files']:
                file_path = os.path.join(UPLOAD_FOLDER, room_id, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
            room_dir = os.path.join(UPLOAD_FOLDER, room_id)
            if os.path.exists(room_dir):
                os.rmdir(room_dir)
            del ROOMS[room_id]
        import time
        time.sleep(60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create-room', methods=['POST'])
def create_room():
    room_id = str(uuid.uuid4())[:6]
    password = request.form['password']
    ROOMS[room_id] = {
        "password": password,
        "expires": datetime.now() + timedelta(minutes=TTL_MINUTES),
        "files": []
    }
    os.makedirs(os.path.join(UPLOAD_FOLDER, room_id))
    flash(f"Room created! Room ID: {room_id}")
    return redirect(url_for('join_room'))

@app.route('/join-room', methods=['GET', 'POST'])
def join_room():
    if request.method == 'POST':
        room_id = request.form['room_id']
        password = request.form['password']
        if room_id in ROOMS and ROOMS[room_id]['password'] == password:
            return redirect(url_for('room', room_id=room_id))
        else:
            flash("Invalid room ID or password")
            return redirect(url_for('join_room'))
    return render_template('join.html')

@app.route('/room/<room_id>', methods=['GET', 'POST'])
def room(room_id):
    if room_id not in ROOMS:
        flash("Room not found or expired")
        return redirect(url_for('join_room'))

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, room_id, filename)
            file.save(file_path)
            ROOMS[room_id]['files'].append(filename)

    file_list = ROOMS[room_id]['files']
    return render_template('room.html', room_id=room_id, files=file_list)

@app.route('/download/<room_id>/<filename>')
def download_file(room_id, filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, room_id), filename, as_attachment=True)

if __name__ == '__main__':
    threading.Thread(target=cleanup_expired_rooms, daemon=True).start()
    app.run(debug=True)
