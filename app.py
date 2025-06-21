from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import google.generativeai as genai
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configure Gemini API
genai.configure(api_key='YOUR-API-KEY')
model = genai.GenerativeModel('gemini-2.0-flash')

# Database Initialization
# Database Initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'agent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tickets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_email TEXT,
            issue TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            category TEXT,
            priority INTEGER DEFAULT 2,
            sentiment INTEGER,
            assigned_to INTEGER,
            deadline TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_to) REFERENCES users(id)
        )
    ''')
    
    # Conversations table
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
      # Metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            ticket_id INTEGER PRIMARY KEY,
            first_response_time INTEGER,
            resolution_time INTEGER,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id)
        )
    ''')
    
    # Email logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_by INTEGER,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'sent',
            FOREIGN KEY (ticket_id) REFERENCES tickets(id),
            FOREIGN KEY (sent_by) REFERENCES users(id)
        )
    ''')
    
    # Create admin user if not exists
    try:
        cursor.execute(
            "INSERT INTO users (name, mobile, email, password, role) VALUES (?, ?, ?, ?, ?)",
            ("Admin", "1234567890", "admin@example.com", generate_password_hash("admin123"), "manager")
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    
    conn.close()

init_db()

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# AI Functions
def analyze_sentiment(text):
    try:
        prompt = f"Analyze sentiment (1-5, 5=angry) of: '{text}'. Respond ONLY with the number."
        return int(model.generate_content(prompt).text)
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return 3  # Default neutral sentiment

def categorize_issue(text):
    try:
        prompt = f"Categorize this issue: '{text}'. Options: [Billing, Technical, Shipping, Account]. Respond ONLY with category."
        return model.generate_content(prompt).text
    except Exception as e:
        print(f"Categorization error: {e}")
        return "Other"

def generate_ai_reply(conversation_history):
    try:
        prompt = f"""
        As a customer support agent, draft a concise reply to this conversation:
        {conversation_history}
        
        Guidelines:
        - Be empathetic
        - Offer solution/next steps
        - Keep under 100 words
        """
        return model.generate_content(prompt).text
    except Exception as e:
        print(f"AI reply generation error: {e}")
        return "Thank you for your message. We're looking into this and will get back to you shortly."

def generate_formal_email(customer_name, customer_email, issue, ticket_id):
    try:
        prompt = f"""
        Generate a formal customer service email response for the following:
        
        Customer Name: {customer_name}
        Customer Email: {customer_email}
        Issue: {issue}
        Ticket ID: #{ticket_id}
        
        Guidelines:
        - Professional and formal tone
        - Address customer by name
        - Acknowledge their concern
        - Provide clear next steps or solution
        - Include ticket reference
        - Professional closing
        - Keep it under 200 words
        
        Format as a complete email with subject and body.
        """
        response = model.generate_content(prompt).text
        
        # Try to split into subject and body
        lines = response.split('\n')
        subject = ""
        body = ""
        
        for i, line in enumerate(lines):
            if 'subject:' in line.lower():
                subject = line.split(':', 1)[1].strip()
                body = '\n'.join(lines[i+1:]).strip()
                break
        
        if not subject:
            subject = f"Re: Your Support Request - Ticket #{ticket_id}"
            body = response
        
        return {
            'subject': subject,
            'body': body
        }
    except Exception as e:
        print(f"Email generation error: {e}")
        return {
            'subject': f"Re: Your Support Request - Ticket #{ticket_id}",
            'body': f"Dear {customer_name},\n\nThank you for contacting our support team regarding your recent inquiry.\n\nWe have received your request and are currently reviewing the details. Our team will investigate this matter and provide you with a resolution as soon as possible.\n\nYour ticket reference number is #{ticket_id}. Please keep this number for your records.\n\nBest regards,\nCustomer Support Team"
        }

# Utility Functions
def calculate_deadline(priority):
    if priority == 1: return datetime.now() + timedelta(hours=12)
    elif priority == 2: return datetime.now() + timedelta(hours=24)
    else: return datetime.now() + timedelta(hours=48)

# Routes
@app.route('/')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tickets WHERE status="Open"')
    open_tickets = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tickets WHERE status="Escalated"')
    escalated_tickets = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(resolution_time) FROM metrics')
    avg_resolution = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT * FROM tickets ORDER BY created_at DESC LIMIT 5')
    recent_tickets = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_agents = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('dashboard.html',
                         open_tickets=open_tickets,
                         escalated_tickets=escalated_tickets,
                         avg_resolution=avg_resolution,
                         recent_tickets=recent_tickets,
                         total_agents=total_agents)

@app.route('/create_ticket', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        issue = request.form.get('issue')
        
        if not customer_name or not issue:
            flash('Customer name and issue are required fields', 'danger')
            return redirect(url_for('create_ticket'))
        
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            
            sentiment = analyze_sentiment(issue)
            category = categorize_issue(issue)
            priority = 3 if sentiment >= 4 else 2
            deadline = calculate_deadline(priority)
            
            cursor.execute('''
                INSERT INTO tickets 
                (customer_name, customer_email, issue, status, category, sentiment, priority, deadline)
                VALUES (?, ?, ?, 'Open', ?, ?, ?, ?)
            ''', (customer_name, customer_email, issue, category, sentiment, priority, deadline))
            
            ticket_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO conversations 
                (ticket_id, sender_type, message)
                VALUES (?, 'customer', ?)
            ''', (ticket_id, issue))
            
            conn.commit()
            flash('Ticket created successfully!', 'success')
            return redirect(url_for('view_ticket', ticket_id=ticket_id))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error creating ticket: {str(e)}', 'danger')
            print(f"Ticket creation error: {e}")
            return redirect(url_for('create_ticket'))
        finally:
            conn.close()
    
    return render_template('create_ticket.html')

@app.route('/ticket/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get ticket details
    cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    
    # Get conversation history
    cursor.execute('''
        SELECT * FROM conversations 
        WHERE ticket_id = ? 
        ORDER BY created_at
    ''', (ticket_id,))
    conversations = cursor.fetchall()
    
    # Get email logs for this ticket
    cursor.execute('''
        SELECT e.*, u.name as sender_name 
        FROM email_logs e
        LEFT JOIN users u ON e.sent_by = u.id
        WHERE e.ticket_id = ? 
        ORDER BY e.sent_at DESC
    ''', (ticket_id,))
    email_logs = cursor.fetchall()
    
    # Get suggested AI reply
    conv_history = "\n".join([f"{c[2]}: {c[3]}" for c in conversations])
    ai_reply = generate_ai_reply(conv_history) if conversations else ""
    
    # Get users for assignment
    cursor.execute('SELECT id, name FROM users WHERE role = "agent"')
    agents = cursor.fetchall()
    
    conn.close()
    
    if not ticket:
        flash('Ticket not found', 'danger')
        return redirect(url_for('ticket_list'))
    
    return render_template('ticket.html',
                         ticket=ticket,
                         conversations=conversations,
                         email_logs=email_logs,
                         ai_reply=ai_reply,
                         agents=agents)

@app.route('/generate_email/<int:ticket_id>')
@login_required
def generate_email(ticket_id):
    if session.get('role') != 'manager':
        flash('Access denied. Only managers can generate emails.', 'danger')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    conn.close()
    
    if not ticket:
        flash('Ticket not found', 'danger')
        return redirect(url_for('ticket_list'))
    
    # Generate formal email
    email_content = generate_formal_email(
        customer_name=ticket[1],
        customer_email=ticket[2],
        issue=ticket[3],
        ticket_id=ticket_id
    )
    
    return render_template('generate_email.html',
                         ticket=ticket,
                         email_content=email_content)

@app.route('/regenerate_email/<int:ticket_id>', methods=['POST'])
@login_required
def regenerate_email(ticket_id):
    if session.get('role') != 'manager':
        flash('Access denied. Only managers can regenerate emails.', 'danger')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    conn.close()
    
    if not ticket:
        flash('Ticket not found', 'danger')
        return redirect(url_for('ticket_list'))
    
    # Get custom instructions if provided
    custom_instructions = request.form.get('custom_instructions', '')
    
    # Generate formal email with custom instructions
    try:
        prompt = f"""
        Generate a formal customer service email response for the following:
        
        Customer Name: {ticket[1]}
        Customer Email: {ticket[2]}
        Issue: {ticket[3]}
        Ticket ID: #{ticket_id}
        
        Additional Instructions: {custom_instructions}
        
        Guidelines:
        - Professional and formal tone
        - Address customer by name
        - Acknowledge their concern
        - Provide clear next steps or solution
        - Include ticket reference
        - Professional closing
        - Keep it under 200 words
        
        Format as a complete email with subject and body.
        """
        response = model.generate_content(prompt).text
        
        # Try to split into subject and body
        lines = response.split('\n')
        subject = ""
        body = ""
        
        for i, line in enumerate(lines):
            if 'subject:' in line.lower():
                subject = line.split(':', 1)[1].strip()
                body = '\n'.join(lines[i+1:]).strip()
                break
        
        if not subject:
            subject = f"Re: Your Support Request - Ticket #{ticket_id}"
            body = response
        
        email_content = {
            'subject': subject,
            'body': body
        }
    except Exception as e:
        print(f"Email regeneration error: {e}")
        email_content = generate_formal_email(ticket[1], ticket[2], ticket[3], ticket_id)
    
    return render_template('generate_email.html',
                         ticket=ticket,
                         email_content=email_content)

@app.route('/send_email/<int:ticket_id>', methods=['POST'])
@login_required
def send_email(ticket_id):
    if session.get('role') != 'manager':
        flash('Access denied. Only managers can send emails.', 'danger')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    
    if not ticket:
        flash('Ticket not found', 'danger')
        return redirect(url_for('ticket_list'))
    
    # Get email data from form
    recipient_email = request.form.get('recipient_email', ticket[2])
    subject = request.form.get('subject', '')
    body = request.form.get('body', '')
    
    if not all([recipient_email, subject, body]):
        flash('All email fields are required', 'danger')
        return redirect(url_for('generate_email', ticket_id=ticket_id))
    
    try:
        # Log the email in database
        cursor.execute('''
            INSERT INTO email_logs 
            (ticket_id, recipient_email, subject, body, sent_by, status)
            VALUES (?, ?, ?, ?, ?, 'sent')
        ''', (ticket_id, recipient_email, subject, body, session['user_id']))
        
        # Add to conversation history
        cursor.execute('''
            INSERT INTO conversations 
            (ticket_id, sender_type, message)
            VALUES (?, 'agent', ?)
        ''', (ticket_id, f"Email sent to {recipient_email}\nSubject: {subject}\nBody: {body[:100]}..."))
        
        conn.commit()
        flash('Email logged successfully! (Note: This is a prototype - email not actually sent via Web3Forms)', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error logging email: {str(e)}', 'danger')
        print(f"Email logging error: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('view_ticket', ticket_id=ticket_id))

@app.route('/tickets')
@login_required
def ticket_list():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get all tickets with optional filtering
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    priority_filter = request.args.get('priority')
    
    query = '''
        SELECT t.*, u.name as assigned_name 
        FROM tickets t 
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE 1=1
    '''
    params = []
    
    if status_filter and status_filter != 'All':
        query += ' AND t.status = ?'
        params.append(status_filter)
    
    if category_filter and category_filter != 'All':
        query += ' AND t.category = ?'
        params.append(category_filter)
    
    if priority_filter and priority_filter != 'All':
        try:
            priority_value = int(priority_filter)
            query += ' AND t.priority = ?'
            params.append(priority_value)
        except ValueError:
            pass  # Ignore invalid priority values
    
    query += ' ORDER BY t.created_at DESC'
    
    cursor.execute(query, params)
    tickets = cursor.fetchall()
    
    conn.close()
    
    return render_template('tickets.html', tickets=tickets)

@app.route('/agents')
def agent_list():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, mobile, role, created_at FROM users')
    agents = cursor.fetchall()
    conn.close()
    return render_template('agents.html', agents=agents)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 8 or not any(c.isdigit() for c in password):
            flash('Password must be at least 8 characters with at least 1 number', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (name, mobile, email, password)
                VALUES (?, ?, ?, ?)
            ''', (name, mobile, email, hashed_password))
            conn.commit()
            flash('Registration successful! Please login', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[4], password):
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['role'] = user[5]
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)