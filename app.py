from flask import Flask, request, render_template, redirect, session, jsonify
import sqlite3
from fuzzywuzzy import fuzz
import pandas as pd
import os

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

def get_answer(question):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM facts")
    rows = cursor.fetchall()

    best_match = None
    best_score = 0
    for db_question, answer in rows:
        score = fuzz.partial_ratio(question.lower(), db_question.lower())
        if score > best_score:
            best_score = score
            best_match = (db_question, answer)

    conn.close()

    if best_score >= 80:
        return {"bot_response": best_match[1], "needs_learning": False}
    else:
        save_unanswered_question(question)
        return {
            "bot_response": "Sorry, I don't have an answer for that. Please call us at +1-800-123-456 for more information.",
            "needs_learning": True
        }

def save_unanswered_question(question):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM unanswered_questions WHERE question = ?", (question,))
    existing = cursor.fetchone()
    if not existing:
        cursor.execute("INSERT INTO unanswered_questions (question) VALUES (?)", (question,))
        conn.commit()
    conn.close()

@app.route('/')
def guest():
    return render_template('guest.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['user'] = 'admin'
            return redirect('/admin')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('user') != 'admin':
        return "Unauthorized", 401

    if request.method == 'POST':
        if 'update_id' in request.form:
            # Admin updating existing FAQ
            update_id = request.form['update_id']
            updated_question = request.form['updated_question']
            updated_answer = request.form['updated_answer']

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("UPDATE facts SET question = ?, answer = ? WHERE id = ?", (updated_question, updated_answer, update_id))
            conn.commit()
            conn.close()
            return redirect('/admin')

        elif 'answer_id' in request.form:
            # Admin answering unanswered question
            answer_id = request.form['answer_id']
            answer_text = request.form['answer_text']

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT question FROM unanswered_questions WHERE id = ?", (answer_id,))
            row = cursor.fetchone()
            if row:
                question = row[0]
                cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (question, answer_text))
                cursor.execute("DELETE FROM unanswered_questions WHERE id = ?", (answer_id,))
                conn.commit()
            conn.close()
            return redirect('/admin')

        elif 'delete_fact_id' in request.form:
            # Admin deleting a FAQ
            delete_id = request.form['delete_fact_id']

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE id = ?", (delete_id,))
            conn.commit()
            conn.close()
            return redirect('/admin')

        elif 'delete_unanswered_id' in request.form:
            # Admin deleting an unanswered question
            delete_unanswered_id = request.form['delete_unanswered_id']

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM unanswered_questions WHERE id = ?", (delete_unanswered_id,))
            conn.commit()
            conn.close()
            return redirect('/admin')

        elif 'excel_file' in request.files:
            # Admin uploading Excel
            file = request.files['excel_file']
            print(file.filename.endswith('.xlsx'))
            if file.filename.endswith('.xlsx'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                # Process Excel
                df = pd.read_excel(filepath)

                if 'Question' in df.columns and 'Answer' in df.columns:
                    conn = sqlite3.connect(DATABASE)
                    cursor = conn.cursor()

                    for index, row in df.iterrows():
                        question = str(row['Question']).strip()
                        answer = str(row['Answer']).strip()

                        cursor.execute("SELECT id FROM facts WHERE question = ?", (question,))
                        exists = cursor.fetchone()
                        if not exists:
                            cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (question, answer))

                    conn.commit()
                    conn.close()
                
                os.remove(filepath)

            return redirect('/admin')

        else:
            # Manually adding question-answer
            question = request.form['question']
            answer = request.form['answer']

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (question, answer))
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
    response = get_answer(question)
    return jsonify(response)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
