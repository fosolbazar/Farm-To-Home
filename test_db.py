import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

print("DATABASE_URL =", DATABASE_URL)

try:
    conn = psycopg2.connect(
        dsn=DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    print("✅ Connected Successfully!")
    conn.close()
except Exception as e:
    print("❌ Error:", e)
