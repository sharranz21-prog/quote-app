from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this'

DB_PATH = '/tmp/quotes.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            emoji TEXT NOT NULL,
            UNIQUE(quote_id, username, emoji)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuoteHub</title>
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #f4f6f8; margin: 0; padding: 0; }
        nav { background: #1e293b; padding: 1rem 2rem; display: flex; justify-space-between: space-between; align-items: center; color: white; }
        nav a { color: #cbd5e1; text-decoration: none; margin-left: 1.5rem; font-weight: 500; }
        nav a:hover { color: white; }
        .container { max-width: 700px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .btn { background: #2563eb; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 600; }
        .btn:hover { background: #1d4ed8; }
        .btn-danger { background: #ef4444; }
        .btn-danger:hover { background: #dc2626; }
        input[type="text"], input[type="password"] { width: 100%; padding: 0.75rem; margin: 0.5rem 0 1rem 0; border: 1px solid #cbd5e1; border-radius: 6px; }
        .quote-text { font-size: 1.25rem; font-weight: 500; color: #0f172a; margin-bottom: 0.5rem; }
        .quote-meta { font-size: 0.875rem; color: #64748b; margin-bottom: 1rem; }
        .reactions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1rem; }
        .reaction-btn { background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 20px; padding: 0.3rem 0.8rem; cursor: pointer; font-size: 0.9rem; transition: background 0.2s; }
        .reaction-btn:hover { background: #e2e8f0; }
        .flash { padding: 0.75rem; background: #dcfce7; color: #166534; border-radius: 6px; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <nav>
        <div style="font-size: 1.4rem; font-weight: bold; color: white;">💬 QuoteHub</div>
        <div>
            {% if session.get('username') %}
                <a href="{{ url_for('feed') }}">Community Feed</a>
                <a href="{{ url_for('profile') }}">My Quotes</a>
                <a href="{{ url_for('logout') }}">Logout ({{ session['username'] }})</a>
            {% else %}
                <a href="{{ url_for('login') }}">Login</a>
                <a href="{{ url_for('register') }}">Register</a>
            {% endif %}
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="flash">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
<div class="card">
    <h2>Join QuoteHub 🚀</h2>
    <form method="POST">
        <label>Username</label>
        <input type="text" name="username" required>
        <label>Password</label>
        <input type="password" name="password" required>
        <button type="submit" class="btn">Create Account</button>
    </form>
    <p style="margin-top: 1rem;">Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
</div>
''')

LOGIN_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
<div class="card">
    <h2>Welcome Back 👋</h2>
    <form method="POST">
        <label>Username</label>
        <input type="text" name="username" required>
        <label>Password</label>
        <input type="password" name="password" required>
        <button type="submit" class="btn">Login</button>
    </form>
    <p style="margin-top: 1rem;">Need an account? <a href="{{ url_for('register') }}">Register here</a></p>
</div>
''')

FEED_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
<div class="card">
    <h3>Post a Quote 💭</h3>
    <form action="{{ url_for('add_quote') }}" method="POST">
        <input type="text" name="content" placeholder="Share a quote, thought, or emotion... 🔥😂❤️" required>
        <button type="submit" class="btn">Post Quote</button>
    </form>
</div>

<h3>Community Feed 🌐</h3>
{% for quote in quotes %}
<div class="card">
    <div class="quote-text">"{{ quote['content'] }}"</div>
    <div class="quote-meta">Posted by <strong>@{{ quote['username'] }}</strong></div>
    
    <div class="reactions">
        {% for emoji in ['🔥', '😂', '❤️', '👏', '💯'] %}
            <form action="{{ url_for('react', quote_id=quote['id']) }}" method="POST" style="display:inline;">
                <input type="hidden" name="emoji" value="{{ emoji }}">
                <button type="submit" class="reaction-btn">
                    {{ emoji }} {{ quote['reactions'].get(emoji, 0) }}
                </button>
            </form>
        {% endfor %}
    </div>
</div>
{% else %}
<div class="card"><p>No quotes posted yet. Be the first!</p></div>
{% endfor %}
''')

PROFILE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
<h2>My Personal Collection 📚</h2>
<div class="card">
    <h3>Post a New Quote 💭</h3>
    <form action="{{ url_for('add_quote') }}" method="POST">
        <input type="text" name="content" placeholder="What's on your mind?" required>
        <button type="submit" class="btn">Post Quote</button>
    </form>
</div>

<h3>My Posts</h3>
{% for quote in quotes %}
<div class="card" style="display: flex; justify-content: space-between; align-items: center;">
    <div>
        <div class="quote-text">"{{ quote['content'] }}"</div>
        <div class="quote-meta">Posted on {{ quote['created_at'] }}</div>
    </div>
    <form action="{{ url_for('delete_quote', quote_id=quote['id']) }}" method="POST">
        <button type="submit" class="btn btn-danger">Delete</button>
    </form>
</div>
{% else %}
<div class="card"><p>You haven't posted any quotes yet.</p></div>
{% endfor %}
''')

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('feed'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_pw))
            conn.commit()
            flash('Account created successfully! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Try another one.')
        finally:
            conn.close()
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            return redirect(url_for('feed'))
        else:
            flash('Invalid username or password.')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/feed')
def feed():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    raw_quotes = conn.execute('SELECT * FROM quotes ORDER BY id DESC').fetchall()
    
    quotes = []
    for q in raw_quotes:
        reactions_raw = conn.execute('SELECT emoji, COUNT(*) as count FROM reactions WHERE quote_id = ? GROUP BY emoji', (q['id'],)).fetchall()
        reaction_counts = {r['emoji']: r['count'] for r in reactions_raw}
        
        quotes.append({
            'id': q['id'],
            'username': q['username'],
            'content': q['content'],
            'created_at': q['created_at'],
            'reactions': reaction_counts
        })
    conn.close()
    
    return render_template_string(FEED_TEMPLATE, quotes=quotes)

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    quotes = conn.execute('SELECT * FROM quotes WHERE username = ? ORDER BY id DESC', (session['username'],)).fetchall()
    conn.close()
    
    return render_template_string(PROFILE_TEMPLATE, quotes=quotes)

@app.route('/add_quote', methods=['POST'])
def add_quote():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    content = request.form['content'].strip()
    if content:
        conn = get_db()
        conn.execute('INSERT INTO quotes (username, content) VALUES (?, ?)', (session['username'], content))
        conn.commit()
        conn.close()
        flash('Quote posted successfully!')
    return redirect(request.referrer or url_for('feed'))

@app.route('/react/<int:quote_id>', methods=['POST'])
def react(quote_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    emoji = request.form['emoji']
    conn = get_db()
    try:
        conn.execute('INSERT INTO reactions (quote_id, username, emoji) VALUES (?, ?, ?)', (quote_id, session['username'], emoji))
        conn.commit()
    except sqlite3.IntegrityError:
        # If user already reacted with this emoji, remove the reaction (toggle off)
        conn.execute('DELETE FROM reactions WHERE quote_id = ? AND username = ? AND emoji = ?', (quote_id, session['username'], emoji))
        conn.commit()
    finally:
        conn.close()
        
    return redirect(url_for('feed'))

@app.route('/delete_quote/<int:quote_id>', methods=['POST'])
def delete_quote(quote_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('DELETE FROM quotes WHERE id = ? AND username = ?', (quote_id, session['username']))
    conn.execute('DELETE FROM reactions WHERE quote_id = ?', (quote_id,))
    conn.commit()
    conn.close()
    
    flash('Quote deleted.')
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True)
