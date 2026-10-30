import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super-secret-key-for-quotes'

DB_PATH = '/tmp/quotes.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote TEXT NOT NULL
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM quotes')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO quotes (quote) VALUES (?)', ('Believing in yourself is the first secret to success.',))
    conn.commit()
    conn.close()

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Login - Quote Generator</title></head>
<body style="font-family: Arial; padding: 40px; background: #f4f4f9;">
    <h2>Login</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: red;">{% for msg in messages %}<li>{{ msg }}</li>{% endfor %}</ul>
      {% endif %}
    {% endwith %}
    <form method="POST">
        <label>Username:</label><br><input type="text" name="username" required><br><br>
        <label>Password:</label><br><input type="password" name="password" required><br><br>
        <button type="submit">Login</button>
    </form>
    <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Register - Quote Generator</title></head>
<body style="font-family: Arial; padding: 40px; background: #f4f4f9;">
    <h2>Register</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: red;">{% for msg in messages %}<li>{{ msg }}</li>{% endfor %}</ul>
      {% endif %}
    {% endwith %}
    <form method="POST">
        <label>Username:</label><br><input type="text" name="username" required><br><br>
        <label>Password:</label><br><input type="password" name="password" required><br><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Dashboard - Quote Generator</title></head>
<body style="font-family: Arial; padding: 40px; background: #f4f4f9;">
    <h2>Welcome, {{ username }}!</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: green;">{% for msg in messages %}<li>{{ msg }}</li>{% endfor %}</ul>
      {% endif %}
    {% endwith %}
    <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h3>Quote of the Day:</h3>
        <p style="font-size: 18px; font-style: italic;">"{{ quote }}"</p>
    </div>
    <form method="POST">
        <label>Add a new quote:</label><br><br>
        <input type="text" name="new_quote" style="width: 300px; padding: 5px;" required>
        <button type="submit" style="padding: 6px 12px;">Update Quote</button>
    </form>
    <br><br>
    <a href="{{ url_for('logout') }}">Logout</a>
</body>
</html>
'''

@app.route('/')
def index():
    init_db()
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    init_db()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    init_db()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            flash('Account created successfully! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('Username already exists!')
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    init_db()
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    if request.method == 'POST':
        new_quote = request.form.get('new_quote')
        if new_quote:
            conn.execute('INSERT INTO quotes (quote) VALUES (?)', (new_quote,))
            conn.commit()
            flash('Quote updated successfully!')

    latest_quote = conn.execute('SELECT quote FROM quotes ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()

    quote_text = latest_quote['quote'] if latest_quote else "No quotes available."
    return render_template_string(DASHBOARD_TEMPLATE, username=session['username'], quote=quote_text)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))