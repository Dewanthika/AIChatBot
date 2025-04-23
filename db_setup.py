import sqlite3

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('data/knowledge.db')
cursor = conn.cursor()

# Create the 'facts' table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS facts (
        question TEXT PRIMARY KEY,
        answer TEXT NOT NULL
    )
''')

# Add some sample Q&A data
sample_data = [
    ('types of accounts', 'We offer Savings, Current, and Fixed Deposit (FD) accounts.'),
    ('interest rates', 'Savings: 3.5%, FD: 6.5% annually, Current: No interest.'),
    ('how to open an account', 'You can open an account online or visit the nearest branch.'),
    ('thank you', 'You are welcome!'),
    ('good morning', 'Good morning! How can I assist you today?')
]

cursor.executemany("INSERT OR IGNORE INTO facts (question, answer) VALUES (?, ?)", sample_data)


# Save and close
conn.commit()
conn.close()

print("Database and table created with sample data.")
