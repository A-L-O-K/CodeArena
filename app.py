from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import random
import string
from datetime import datetime, timedelta
import psycopg2
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

load_dotenv()

database = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")

conn = psycopg2.connect(
    database=database,
    user=user,
    password=password,
    host=host,
    port=port
)

cur = conn.cursor()

def select_random_function():
    cur.execute("select question_id from questions")
    lis = list(cur)
    question_id = random.choice(lis)[0]
    cur.execute(f"select description from questions where question_id = {question_id}")
    for i in cur:
        return i[0]

rooms = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur.execute(f"select username, password from players where email = '{email}'")
        dataFromBase = list(cur)
        if dataFromBase:
            if dataFromBase[0][1] == password: # [0][1] is password
                session['username'] = dataFromBase[0][0] # [0][0] is username
                return redirect(url_for('index'))
        else:
            return 'Invalid credentials', 400
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        cur.execute(f"select email from players where email = '{email}'")
        dataFromBase = list(cur)
        if dataFromBase:
            return 'Email already registered', 400
        else:
            cur.execute(f"INSERT INTO players (username, email, password, wins_count) VALUES ('{username}', '{email}', '{password}', {0})")
            conn.commit()
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/room', methods=['POST'])
def room():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    action = request.form['action']
    if action == 'create':
        room_code = generate_room_code()
        selected_word = select_random_function()
        rooms[room_code] = {
            'users': [username],
            'word': selected_word,
            'game_over': False,
            'winner': None,
            'start_time': None,
            'countdown_seconds': 15 * 60
        }
        return redirect(url_for('chat', room_code=room_code, username=username))
    elif action == 'join':
        room_code = request.form['room_code']
        if room_code in rooms and len(rooms[room_code]['users']) < 2:
            rooms[room_code]['users'].append(username)
            if len(rooms[room_code]['users']) == 2:
                rooms[room_code]['start_time'] = datetime.now()
                word_to_reveal = rooms[room_code]['word']
                socketio.emit('reveal_word', {'word': word_to_reveal}, room=room_code)
            return redirect(url_for('chat', room_code=room_code, username=username))
        else:
            return "Room is full or doesn't exist", 400
    else:
        return redirect(url_for('index'))

@app.route('/chat/<room_code>/<username>')
def chat(room_code, username):
    if room_code not in rooms or username not in rooms[room_code]['users']:
        return redirect(url_for('index'))
    return render_template('chat.html', room_code=room_code, username=username)

@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send(f"{username} has entered the room.", to=room)
    if room in rooms and len(rooms[room]['users']) == 2 and rooms[room]['start_time'] is not None:
        word_to_reveal = rooms[room]['word']
        socketio.emit('reveal_word', {'word': word_to_reveal}, room=room)
        countdown_seconds = rooms[room].get('countdown_seconds', 0)
        start_time = rooms[room]['start_time']
        elapsed_time = (datetime.now() - start_time).total_seconds()
        remaining_seconds = countdown_seconds - elapsed_time
        if remaining_seconds > 0:
            socketio.emit('start_timer', {'countdown_seconds': int(remaining_seconds)}, room=room)
        else:
            socketio.emit('time_out', {}, room=room)
            del rooms[room]

@socketio.on('message')
def handle_message(data):
    room = data['room']
    username = data['username']
    message = data['message']
    sender_sid = request.sid

    if message.strip().lower() == rooms[room]['word'].lower() and not rooms[room]['game_over']:
        rooms[room]['game_over'] = True
        rooms[room]['winner'] = username
        socketio.emit('game_over', {'message': f'Game Over! {username} won!'}, room=room)
        socketio.emit('word_guessed', {'result': 'correct'}, room=sender_sid)
        socketio.emit('redirect_home', {}, room=room)
    else:
        socketio.emit('word_guessed', {'result': 'incorrect'}, room=sender_sid)

@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    if room in rooms:
        if username in rooms[room]['users']:
            rooms[room]['users'].remove(username)
        if len(rooms[room]['users']) == 0:
            del rooms[room]
        else:
            rooms[room]['game_over'] = True
            socketio.emit('player_left', {}, room=room)
            socketio.emit('redirect_home', {}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
