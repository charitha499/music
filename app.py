from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

# Ensure 'static/music' folder exists
if not os.path.exists('static/music'):
    os.makedirs('static/music')

# Initialize Database: Songs, Favorites, and Users tables
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Create the songs table with play_count column if it doesn't already exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS songs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        play_count INTEGER DEFAULT 0)''')
    
    # Create the favorites table
    cursor.execute('''CREATE TABLE IF NOT EXISTS favorites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        song_id INTEGER NOT NULL,
                        FOREIGN KEY (song_id) REFERENCES songs(id))''')
    
    # Create the users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
    
    conn.commit()
    conn.close()

# Call this function to create the tables
init_db()

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Connect to the database and retrieve song data including play_count
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, artist, filename, play_count FROM songs')
    songs = cursor.fetchall()  # Fetch all songs with play_count
    conn.close()
    
    return render_template('home.html', songs=songs, username=session.get('username'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form['title']
        artist = request.form['artist']
        file = request.files['file']

        # Save file to static/music folder
        file_path = os.path.join('static/music', file.filename)
        file.save(file_path)

        # Save song details to the database
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO songs (title, artist, filename) VALUES (?, ?, ?)', 
                       (title, artist, file.filename))
        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    return render_template('upload.html')

@app.route('/favorites', methods=['GET'])
@login_required
def favorites():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT songs.id, songs.title, songs.artist, songs.filename 
        FROM favorites 
        JOIN songs ON favorites.song_id = songs.id
    ''')
    favorite_songs = cursor.fetchall()
    conn.close()
    return render_template('favorites.html', favorite_songs=favorite_songs)

@app.route('/add_favorite/<int:song_id>', methods=['GET'])
@login_required
def add_favorite(song_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO favorites (song_id) VALUES (?)', (song_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/remove_favorite/<int:song_id>', methods=['GET'])
@login_required
def remove_favorite(song_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM favorites WHERE song_id = ?', (song_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('favorites'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)  # Hash the password for security

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                           (username, hashed_password))
            conn.commit()
            conn.close()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Try a different one.', 'error')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):  # Verify hashed password
            session['user_id'] = user[0]  # Store user ID in session
            session['username'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# New route to increment play count when a song is played
@app.route('/play_song/<int:song_id>', methods=['POST'])
@login_required
def play_song(song_id):
    # Increment play count
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE songs SET play_count = play_count + 1 WHERE id = ?', (song_id,))
    conn.commit()
    conn.close()

    # Redirect back to the home page or wherever
    flash('Song played!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
