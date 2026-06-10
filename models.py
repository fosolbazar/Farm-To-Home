import sqlite3

DB = "database.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# -------- USERS --------
def create_user(username, password, role, mobile):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO users(username,password,role,mobile)
    VALUES (?,?,?,?)
    """, (username, password, role, mobile))

    conn.commit()
    conn.close()


# -------- PRODUCTS --------
def add_product(name, price, category, stock, image, farmer_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO products(name,price,category,stock,image,farmer_id,approved)
    VALUES (?,?,?,?,?,?,0)
    """, (name, price, category, stock, image, farmer_id))

    conn.commit()
    conn.close()