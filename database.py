
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

database = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")

conn = psycopg2.connect(
    database=database,
    user=user,
    password=password,
    host=host,
    port=port
)

cur = conn.cursor()

# -----------------------------

admins = """
    CREATE TABLE admins (
        admin_id SERIAL PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL
    );
"""

players = """
    CREATE TABLE players (
        player_id SERIAL PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL,
        wins_count INTEGER
    );
"""

competition = """
    CREATE TABLE competition (
        competition_id SERIAL PRIMARY KEY,
        participant1_id INTEGER NOT NULL,
        participant2_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        winner_id INTEGER NOT NULL
    );
"""

code_submission = """
    CREATE TABLE code_submission (
        submission_id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        competition_id INTEGER NOT NULL,
        code TEXT,
        language VARCHAR(255)
    );
"""

questions = """
    CREATE TABLE questions (
        question_id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        difficulty INTEGER NOT NULL,
        solution_id INTEGER,
        user_id INTEGER
    );
"""

solutions = """
    CREATE TABLE solutions (
        solution_id SERIAL PRIMARY KEY,
        language VARCHAR(255) NOT NULL,
        code TEXT NOT NULL,
        question_id INTEGER
    );
"""


cur.execute(admins)
cur.execute(players)
cur.execute(questions)
cur.execute(solutions)
cur.execute(competition)
cur.execute(code_submission)


# -----------------------------

conn.commit()
cur.close()