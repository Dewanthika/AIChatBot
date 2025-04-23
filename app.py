from flask import Flask, request, jsonify, render_template
import sqlite3
from fuzzywuzzy import fuzz

app = Flask(__name__)
DATABASE = 'bankbot.db'

def get_answer(question):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM facts")
    rows = cursor.fetchall()
    conn.close()

    best_match = None
    best_score = 0
    for db_question, answer in rows:
        score = fuzz.partial_ratio(question.lower(), db_question.lower())
        if score > best_score:
            best_score = score
            best_match = (db_question, answer)

    if best_score >= 80:
        return {"bot_response": best_match[1], "needs_learning": False}
    else:
        return {
            "bot_response": f"I don't know the answer to: '{question}'. Can you please teach me?",
            "needs_learning": True,
            "question": question
        }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_message = request.form['message']
    result = get_answer(user_message)
    return jsonify(result)

@app.route('/teach', methods=['POST'])
def teach():
    data = request.get_json()
    question = data['question']
    answer = data['answer']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)", (question, answer))
    conn.commit()
    conn.close()

    return jsonify({"message": "Thanks! I have learned the new answer."})

if __name__ == '__main__':
    app.run(debug=True)
