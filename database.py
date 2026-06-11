import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS users")
cur.execute("DROP TABLE IF EXISTS products")
cur.execute("DROP TABLE IF EXISTS cart")
cur.execute("DROP TABLE IF EXISTS orders")

conn.commit()
conn.close()

print("Database Reset Done")