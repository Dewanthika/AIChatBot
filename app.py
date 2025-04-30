from flask import Flask, request, render_template, redirect, session, jsonify
import sqlite3
from fuzzywuzzy import fuzz
import pandas as pd
import os
import nltk
from nltk.stem import WordNetLemmatizer
import json

# Uncomment if running for the first time
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('punkt_tab')

lemmatizer = WordNetLemmatizer()

app = Flask(__name__)
app.secret_key = '12345'
DATABASE = 'bank.db'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unanswered_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def preprocess_text(text):
    tokens = nltk.word_tokenize(text.lower())
    return ' '.join([lemmatizer.lemmatize(word) for word in tokens])

def get_answer(user_question):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM facts")
    rows = cursor.fetchall()
    conn.close()

    user_processed = preprocess_text(user_question)
    best_match = None
    best_score = 0

    for db_question, answer in rows:
        db_processed = preprocess_text(db_question)
        partial = fuzz.partial_ratio(user_processed, db_processed)
        token_sort = fuzz.token_sort_ratio(user_processed, db_processed)
        token_set = fuzz.token_set_ratio(user_processed, db_processed)
        score = (partial * 0.3) + (token_sort * 0.3) + (token_set * 0.4)
        if score > best_score:
            best_score = score
            best_match = answer

    if best_score >= 75:
        return {"bot_response": best_match, "needs_learning": False}
    else:
        save_unanswered_question(user_question)
        return {"bot_response": "Sorry, I don't have an answer for that. Please call us at +1-800-123-456.", "needs_learning": True}

def save_unanswered_question(question):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM unanswered_questions WHERE question = ?", (question,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO unanswered_questions (question) VALUES (?)", (question,))
        conn.commit()
    conn.close()

@app.route('/')
def guest():
    return render_template('guest.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['user'] = 'admin'
            return redirect('/admin')
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('user') != 'admin':
        return "Unauthorized", 401

    if request.method == 'POST':
        form = request.form
        files = request.files

        if 'update_id' in form:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("UPDATE facts SET question = ?, answer = ? WHERE id = ?", (form['updated_question'], form['updated_answer'], form['update_id']))
            conn.commit()
            conn.close()

        elif 'answer_id' in form:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT question FROM unanswered_questions WHERE id = ?", (form['answer_id'],))
            row = cursor.fetchone()
            if row:
                cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (row[0], form['answer_text']))
                cursor.execute("DELETE FROM unanswered_questions WHERE id = ?", (form['answer_id'],))
                conn.commit()
            conn.close()

        elif 'delete_fact_id' in form:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE id = ?", (form['delete_fact_id'],))
            conn.commit()
            conn.close()

        elif 'delete_unanswered_id' in form:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM unanswered_questions WHERE id = ?", (form['delete_unanswered_id'],))
            conn.commit()
            conn.close()

        elif 'excel_file' in files and files['excel_file'].filename.endswith('.xlsx'):
            file = files['excel_file']
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            df = pd.read_excel(path)
            if 'Question' in df.columns and 'Answer' in df.columns:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                for _, row in df.iterrows():
                    question = str(row['Question']).strip()
                    answer = str(row['Answer']).strip()
                    cursor.execute("SELECT id FROM facts WHERE question = ?", (question,))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (question, answer))
                conn.commit()
                conn.close()
            os.remove(path)

        elif 'intents_file' in files and files['intents_file'].filename.endswith('.json'):
            file = files['intents_file']
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            for intent in data.get('intents', []):
                for pattern in intent.get('patterns', []):
                    for response in intent.get('responses', []):
                        cursor.execute("SELECT id FROM facts WHERE question = ?", (pattern,))
                        if not cursor.fetchone():
                            cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (pattern, response))
            conn.commit()
            conn.close()
            os.remove(path)

        elif 'question' in form and 'answer' in form:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (form['question'], form['answer']))
            conn.commit()
            conn.close()

        return redirect('/admin')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer FROM facts")
    data = cursor.fetchall()
    cursor.execute("SELECT id, question FROM unanswered_questions")
    unanswered = cursor.fetchall()
    conn.close()

    return render_template('admin.html', data=data, unanswered=unanswered)

@app.route('/ask', methods=['POST'])
def ask():
    question = request.form['question']
    return jsonify(get_answer(question))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
