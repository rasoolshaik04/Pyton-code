from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import sqlite3
import os
from datetime import datetime
import uuid
import mimetypes

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-!' # Change this to random string

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'mp4', 'avi', 'mov', 'webm', 'ogg'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database setup
DB_FILE = 'chat.db'

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY, 
                  username TEXT UNIQUE, 
                  password TEXT)''')
    
    # Messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id TEXT PRIMARY KEY,
                  sender_id TEXT,
                  receiver_id TEXT,
                  content TEXT,
                  timestamp TEXT,
                  FOREIGN KEY(sender_id) REFERENCES users(id),
                  FOREIGN KEY(receiver_id) REFERENCES users(id))''')
    
    # Files table
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id TEXT PRIMARY KEY,
                  sender_id TEXT,
                  receiver_id TEXT,
                  filename TEXT,
                  original_filename TEXT,
                  file_type TEXT,
                  file_size INTEGER,
                  timestamp TEXT,
                  FOREIGN KEY(sender_id) REFERENCES users(id),
                  FOREIGN KEY(receiver_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

# Generate encryption key (same for all users - for demo, use secure method in production)
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('register.html', error='Username and password required')
        
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            user_id = str(uuid.uuid4())
            c.execute('INSERT INTO users VALUES (?, ?, ?)',
                     (user_id, username, generate_password_hash(password)))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Username already exists')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, username FROM users WHERE id != ?', (session['user_id'],))
    users = c.fetchall()
    conn.close()
    
    return render_template('dashboard.html', users=users, current_user=session['username'])

@app.route('/chat/<receiver_id>')
def chat(receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE id = ?', (receiver_id,))
    receiver = c.fetchone()
    conn.close()
    
    if not receiver:
        return redirect(url_for('dashboard'))
    
    return render_template('chat.html', 
                          receiver_id=receiver_id,
                          receiver_name=receiver[0],
                          current_user=session['username'])

@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json
    sender_id = session.get('user_id')
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not sender_id or not receiver_id or not content:
        return jsonify({'error': 'Missing data'}), 400
    
    try:
        # Encrypt message
        encrypted_content = cipher.encrypt(content.encode()).decode()
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        msg_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('INSERT INTO messages VALUES (?, ?, ?, ?, ?)',
                 (msg_id, sender_id, receiver_id, encrypted_content, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message_id': msg_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_messages/<receiver_id>')
def get_messages(receiver_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    sender_id = session['user_id']
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get messages between user and receiver (both directions)
    c.execute('''SELECT id, sender_id, content, timestamp FROM messages 
                 WHERE (sender_id = ? AND receiver_id = ?) 
                    OR (sender_id = ? AND receiver_id = ?)
                 ORDER BY timestamp ASC''',
             (sender_id, receiver_id, receiver_id, sender_id))
    
    messages = c.fetchall()
    conn.close()
    
    result = []
    for msg_id, msg_sender_id, encrypted_content, timestamp in messages:
        try:
            # Decrypt message
            decrypted_content = cipher.decrypt(encrypted_content.encode()).decode()
        except:
            decrypted_content = "[Decryption failed]"
        
        result.append({
            'id': msg_id,
            'sender_id': msg_sender_id,
            'is_sent': msg_sender_id == sender_id,
            'content': decrypted_content,
            'timestamp': timestamp
        })
    
    return jsonify(result)

@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    receiver_id = request.form.get('receiver_id')
    
    if file.filename == '' or not receiver_id:
        return jsonify({'error': 'Missing data'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        sender_id = session['user_id']
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        file_size = os.path.getsize(filepath)
        file_type = mimetypes.guess_type(original_filename)[0] or 'unknown'
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('INSERT INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                 (file_id, sender_id, receiver_id, unique_filename, original_filename, file_type, file_size, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': original_filename,
            'mime_type': file_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_files/<receiver_id>')
def get_files(receiver_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    sender_id = session['user_id']
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''SELECT id, sender_id, original_filename, file_type, file_size, timestamp FROM files
                 WHERE (sender_id = ? AND receiver_id = ?) 
                    OR (sender_id = ? AND receiver_id = ?)
                 ORDER BY timestamp ASC''',
             (sender_id, receiver_id, receiver_id, sender_id))
    
    files = c.fetchall()
    conn.close()
    
    result = []
    for file_id, file_sender_id, original_filename, file_type, file_size, timestamp in files:
        result.append({
            'id': file_id,
            'sender_id': file_sender_id,
            'is_sent': file_sender_id == sender_id,
            'filename': original_filename,
            'mime_type': file_type,
            'file_size': file_size,
            'timestamp': timestamp
        })
    
    return jsonify(result)

@app.route('/download/<file_id>')
def download_file(file_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT filename, original_filename FROM files WHERE id = ? AND (sender_id = ? OR receiver_id = ?)',
             (file_id, session['user_id'], session['user_id']))
    file_info = c.fetchone()
    conn.close()
    
    if not file_info:
        return jsonify({'error': 'File not found'}), 404
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_info[0])
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, as_attachment=True, download_name=file_info[1])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
