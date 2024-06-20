from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_sqlalchemy import SQLAlchemy
from models import db, User
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
socketio = SocketIO(app)

with app.app_context():
    db.create_all()

rooms = {}
words = {}

# Load words from file into a dictionary for quick access
with open('words.txt', 'r') as file:
    words = {line.strip().lower(): line.strip() for line in file}

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
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['username'] = user.username
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
        if User.query.filter_by(email=email).first() is None:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
        else:
            return 'Email already registered', 400
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
        selected_word = random.choice(list(words.values()))
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

if __name__ == '__main__':
    socketio.run(app, debug=True)
