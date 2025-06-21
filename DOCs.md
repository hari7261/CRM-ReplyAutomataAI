# AI-Powered Customer Support System Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Core Features](#core-features)
3. [Technical Architecture](#technical-architecture)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [AI Integration](#ai-integration)
7. [Authentication Flow](#authentication-flow)
8. [Error Handling](#error-handling)
9. [Deployment Guide](#deployment-guide)
10. [Future Enhancements](#future-enhancements)

## System Overview <a name="system-overview"></a>
An intelligent ticketing system that automates customer support processes using:
- Flask backend with RESTful API
- Google Gemini for AI-powered responses
- SQLite database for data persistence
- Role-based access control

## Core Features <a name="core-features"></a>
1. **Automated Ticket Processing**
   - AI categorization and prioritization
   - Sentiment analysis (1-5 scale)
   - SLA deadline calculation

2. **Conversation Management**
   - Full conversation history
   - Context-aware responses
   - Human-in-the-loop approval

3. **Performance Analytics**
   - Response time tracking
   - Resolution metrics
   - Agent productivity

## Technical Architecture <a name="technical-architecture"></a>
```
Client (Browser) 
  │
  ├── Flask Application (Python)
  │   ├── Routes/Controllers
  │   ├── AI Service (Gemini)
  │   └── Database ORM
  │
  └── SQLite Database
      ├── Users
      ├── Tickets
      └── Conversations
```

## Database Schema <a name="database-schema"></a>

### Users Table
```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'agent',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
```

### Tickets Table
```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        issue TEXT NOT NULL,
        status TEXT DEFAULT 'Open',
        category TEXT,
        priority INTEGER DEFAULT 2,
        sentiment INTEGER,
        deadline TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
```

### Conversations Table
```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        sender_type TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    )
''')
```

## API Endpoints <a name="api-endpoints"></a>

### Authentication
| Endpoint       | Method | Description               |
|----------------|--------|---------------------------|
| `/register`    | POST   | User registration         |
| `/login`       | POST   | User authentication       |
| `/logout`      | GET    | Session termination       |

### Ticket Management
| Endpoint               | Method | Description                     |
|------------------------|--------|---------------------------------|
| `/tickets`             | GET    | List all tickets               |
| `/tickets`             | POST   | Create new ticket              |
| `/ticket/<ticket_id>`  | GET    | Get ticket details             |
| `/ticket/<ticket_id>`  | POST   | Add response to ticket         |

## AI Integration <a name="ai-integration"></a>

### Sentiment Analysis
```python
def analyze_sentiment(text):
    prompt = f"Analyze sentiment (1-5, 5=angry) of: '{text}'. Respond ONLY with number."
    try:
        return int(model.generate_content(prompt).text)
    except:
        return 3  # Default neutral
```

### Response Generation
```python
def generate_response(conversation_history):
    prompt = f"""As a support agent, draft a concise reply to:
    {conversation_history}
    Guidelines:
    - Be empathetic
    - Offer solution/next steps
    - Keep under 100 words"""
    return model.generate_content(prompt).text
```

## Authentication Flow <a name="authentication-flow"></a>

### Registration
```python
@app.route('/register', methods=['POST'])
def register():
    hashed_pw = generate_password_hash(request.form['password'])
    cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                  (request.form['name'], request.form['email'], hashed_pw))
    conn.commit()
```

### Login
```python
@app.route('/login', methods=['POST'])
def login():
    user = cursor.execute('SELECT * FROM users WHERE email = ?', 
                         (request.form['email'],)).fetchone()
    if user and check_password_hash(user['password'], request.form['password']):
        session['user_id'] = user['id']
```

## Error Handling <a name="error-handling"></a>

### Database Operations
```python
try:
    conn = sqlite3.connect('database.db')
    # Database operations
except sqlite3.Error as e:
    flash(f"Database error: {str(e)}", 'danger')
    conn.rollback()
finally:
    conn.close()
```

### AI Service Fallbacks
```python
try:
    ai_response = model.generate_content(prompt).text
except Exception as e:
    ai_response = "We're looking into your issue and will respond shortly."
```

## Deployment Guide <a name="deployment-guide"></a>

### Requirements
```bash
pip install flask google-generativeai werkzeug
```

### Configuration
1. Set environment variables:
   ```bash
   export FLASK_SECRET_KEY='your_secret_key'
   export GEMINI_API_KEY='your_api_key'
   ```

2. Initialize database:
   ```python
   python -c "from app import init_db; init_db()"
   ```

### Running
```bash
flask run --host=0.0.0.0 --port=5000
```

## Future Enhancements <a name="future-enhancements"></a>
1. **Real-time Notifications**
   - WebSocket integration for live updates
2. **Multi-channel Support**
   - Email, WhatsApp, and social media integration
3. **Advanced Analytics**
   - Predictive modeling for ticket volumes
4. **Mobile Optimization**
   - Responsive design for mobile agents

---

