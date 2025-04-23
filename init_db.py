import sqlite3

# Connect to the database (creates new file if it doesn't exist)
conn = sqlite3.connect('bankbot.db')
cursor = conn.cursor()

# Drop old table just in case (clean reset)
cursor.execute("DROP TABLE IF EXISTS facts")

# Create fresh table
cursor.execute('''
    CREATE TABLE facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL
    )
''')

# Insert sample data
cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)",
               ("what are the types of accounts", "We offer savings, current, and fixed deposit accounts."))

cursor.execute("INSERT INTO facts (question, answer) VALUES (?, ?)",
               ("good morning", "Good morning! How can I help you today?"))

conn.commit()
conn.close()

print("✅ New database created with fresh 'facts' table.")
