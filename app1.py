from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
app = Flask(__name__)
app.secret_key = "farm to home"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT,
        mobile TEXT)""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        image TEXT,
        farmer_id INTEGER,
        approved INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        qty INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)
    cur.execute(
        "SELECT * FROM users WHERE username=?",
        ("admin",)
    )

    admin = cur.fetchone()

    if not admin:
        cur.execute("""
        INSERT INTO users(username,password,role,mobile)
        VALUES (?,?,?,?)
        """, ("admin", "1234", "admin", "0000000000"))
    conn.commit()
    conn.close()


init_db()


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/about")
def about():
    return render_template("about.html")
def get_market_price(price):
    return round(float(price) * 1.20)
# ---------------- AUTH ----------------
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO users(username,password,role,mobile)
        VALUES (?,?,?,?)
        """, (
            request.form["username"],
            request.form["password"],
            request.form["role"],
            request.form["mobile"]
        ))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("auth/signup.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        SELECT * FROM users
        WHERE username=? AND password=?
        """, (request.form["username"], request.form["password"]))

        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            if user["role"] == "admin":
                return redirect("/admin")
            elif user["role"] == "farmer":
                return redirect("/farmer")
            else:
                return redirect("/marketplace")

        else:
            print("LOGIN FAILED")   # debug
            return "Login Failed ❌ Wrong username/password"

    return render_template("auth/login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/admin/products")
def admin_products():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    return render_template("admin/products.html", products=products)
@app.route("/approve/<int:pid>")
def approve(pid):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE products SET approved=1 WHERE id=?", (pid,))
    conn.commit()
    conn.close()

    return redirect("/admin/products")
# ---------------- FARMER ----------------
@app.route("/farmer", methods=["GET","POST"])
def farmer():
    if session.get("role") != "farmer":
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        img = request.files["image"]
        filename = img.filename
        img.save(os.path.join(UPLOAD_FOLDER, filename))

        cur.execute("""
        INSERT INTO products(name,price,image,farmer_id,approved)
        VALUES (?,?,?,?,0)
        """, (
            request.form["name"],
            request.form["price"],
            filename,
            session["user_id"]
        ))

        conn.commit()

    cur.execute("""
    SELECT * FROM products
    WHERE farmer_id=?
    """, (session["user_id"],))

    products = cur.fetchall()
    conn.close()

    return render_template("farmer/dashboard.html", products=products)
@app.route("/farmer/edit/<int:pid>", methods=["GET", "POST"])
def edit_product(pid):
    if session.get("role") != "farmer":
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # শুধু নিজের product edit করতে পারবে
    cur.execute("SELECT * FROM products WHERE id=? AND farmer_id=?",
                (pid, session["user_id"]))
    product = cur.fetchone()

    if not product:
        return "Not allowed"

    if request.method == "POST":
        new_price = request.form["price"]

        cur.execute("""
        UPDATE products
        SET price=?
        WHERE id=? AND farmer_id=?
        """, (new_price, pid, session["user_id"]))

        conn.commit()
        conn.close()

        return redirect("/farmer")

    conn.close()
    return render_template("farmer/edit.html", product=product)

# ---------------- MARKETPLACE ----------------
@app.route("/marketplace")
def marketplace():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM products
    """)

    products = cur.fetchall()

    product_list = []

    for p in products:

        item = dict(p)

        item["market_price"] = get_market_price(p["price"])

        product_list.append(item)

    conn.close()

    return render_template(
        "buyer/marketplace.html",
        products=product_list
    )
# ---------------- CART ----------------
@app.route("/cart/add/<int:pid>")
def add_cart(pid):
    if not session.get("user_id"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO cart(user_id,product_id,qty)
    VALUES (?,?,1)
    """, (session["user_id"], pid))

    conn.commit()
    conn.close()

    return redirect("/cart")
@app.route("/cart")
def cart():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT cart.id, cart.qty, products.name, products.price
    FROM cart
    JOIN products ON cart.product_id = products.id
    WHERE cart.user_id=?
    """, (session["user_id"],))

    items = cur.fetchall()

    fixed_items = []
    total = 0

    for i in items:

        item = dict(i)

        # 🔥 ALWAYS MARKET PRICE
        market_price = get_market_price(i["price"])

        item["market_price"] = market_price

        item["total"] = market_price * i["qty"]

        total += item["total"]

        fixed_items.append(item)

    conn.close()

    return render_template(
        "buyer/cart.html",
        items=fixed_items,
        total=total
    )
@app.route("/cart/remove/<int:cid>")
def remove_cart(cid):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM cart WHERE id=?", (cid,))

    conn.commit()
    conn.close()

    return redirect("/cart")
# ---------------- CHECKOUT ----------------
@app.route("/checkout")
def checkout():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT cart.id, cart.qty, products.name, products.price
    FROM cart
    JOIN products ON cart.product_id = products.id
    WHERE cart.user_id=?
    """, (session["user_id"],))

    items = cur.fetchall()
    conn.close()

    if not items:
        return "Cart is empty"

    # calculate total (20% platform rule)
    total = sum(
        get_market_price(i["price"]) * i["qty"]
        for i in items
    )

    return render_template("buyer/checkout.html", items=items, total=total)

@app.route("/payment", methods=["POST"])
def payment():

    conn = get_db()
    cur = conn.cursor()

    user_id = session["user_id"]

    cur.execute("""
    SELECT cart.product_id, cart.qty, products.price
    FROM cart
    JOIN products ON cart.product_id = products.id
    WHERE cart.user_id=?
    """, (user_id,))

    items = cur.fetchall()

    total = sum(
        get_market_price(i["price"]) * i["qty"]
        for i in items
    )

    # 💰 SAVE ORDER
    cur.execute("""
    INSERT INTO orders(user_id,total,payment_method,status)
    VALUES (?,?,?,'Pending')
    """, (
        user_id,
        total,
        request.form["payment"]
    ))

    order_id = cur.lastrowid

    # 🧹 CLEAR CART
    cur.execute("DELETE FROM cart WHERE user_id=?", (user_id,))

    conn.commit()
    conn.close()

    return redirect(f"/invoice/{order_id}")
@app.route("/invoice/<int:order_id>")
def invoice(order_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM orders WHERE id=?
    """, (order_id,))

    order = cur.fetchone()

    conn.close()

    return render_template("buyer/invoice.html", order=order)
@app.route("/admin/profit")
def profit():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT SUM(total) FROM orders")
    total_revenue = cur.fetchone()[0] or 0

    # 💰 Farmer commission 20%
    farmer_cut = total_revenue * 0.80
    platform_profit = total_revenue * 0.20

    return render_template("admin/profit.html",
                           revenue=total_revenue,
                           farmer=farmer_cut,
                           profit=platform_profit)
def calculate_cart(user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT products.price, cart.qty
    FROM cart
    JOIN products
    ON cart.product_id = products.id
    WHERE cart.user_id=?
    """, (user_id,))

    items = cur.fetchall()

    subtotal = sum(
        round(float(i["price"]) * 1.20)
        * i["qty"]
        for i in items
    )

    conn.close()

    return subtotal
def apply_ecom_rules(subtotal):
    discount = 0

    # 🎯 Discount Rule
    if subtotal >= 500:
        discount = subtotal * 0.10   # 10% discount

    delivery_charge = 50 if subtotal < 300 else 20

    after_discount = subtotal - discount

    total = after_discount + delivery_charge

    return {
        "subtotal": subtotal,
        "discount": discount,
        "delivery": delivery_charge,
        "total": total
    }

# ---------------- ORDERS ----------------
@app.route("/orders")
def orders():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM orders
    WHERE user_id=?
    """, (session["user_id"],))

    orders = cur.fetchall()
    conn.close()

    return render_template("buyer/orders.html", orders=orders)

@app.route("/Meet Team")
def Meet_Team():
    return render_template("Meet Team.html")
# ---------------- ADMIN SIMPLE ----------------
@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    products = cur.fetchone()[0]

    return render_template("admin/dashboard.html",
                           users=users,
                           products=products)

# ---------------- COURIER ----------------
@app.route("/courier")
def courier():
    return render_template("courier/dashboard.html")


if __name__ == "__main__":
    app.run()