from flask import Flask, render_template, request, redirect, session
import os, psycopg2, psycopg2.extras
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "farm to home"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:1298@localhost:5432/farm2home_db")
def get_db():
    return psycopg2.connect(
        dsn=DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- AUTH ----------------
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users(username,password,role,mobile)
            VALUES (%s,%s,%s,%s)
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
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s",
                    (request.form["username"], request.form["password"]))
        user = cur.fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            if user["role"] == "admin":
                return redirect("/admin")
            elif user["role"] == "farmer":
                return redirect("/farmer")
            elif user["role"] == "courier":
                return redirect("/courier")
            else:
                return redirect("/marketplace")
        return "Login Failed ❌"
    return render_template("auth/login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- FARMER ----------------
@app.route("/farmer")
def farmer_dashboard():
    if session.get("role") != "farmer":
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE farmer_id=%s", (session["user_id"],))
    products = cur.fetchall()
    conn.close()
    return render_template("farmer/dashboard.html", products=products)

@app.route("/farmer/upload", methods=["GET","POST"])
def upload_product():
    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        qty = request.form.get("qty")
        image = request.files.get("image")
        filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, filename))
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO products(name,price,qty,image,farmer_id,approved)
            VALUES (%s,%s,%s,%s,%s,0)
        """, (name, price, qty, filename, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect("/farmer")
    return render_template("farmer/upload_product.html")

@app.route("/farmer/profile")
def farmer_profile():
    if session.get("role") != "farmer":
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    farmer = cur.fetchone()
    cur.execute("SELECT * FROM products WHERE farmer_id=%s", (session["user_id"],))
    products = cur.fetchall()
    conn.close()
    return render_template("farmer/profile.html", farmer=farmer, products=products)
@app.route("/farmer/edit/<int:pid>", methods=["GET","POST"])
def farmer_edit_product(pid):
    if session.get("role") != "farmer":
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s AND farmer_id=%s", (pid, session["user_id"]))
    product = cur.fetchone()

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        qty = request.form.get("qty")
        cur.execute("""
            UPDATE products SET name=%s, price=%s, qty=%s WHERE id=%s AND farmer_id=%s
        """, (name, price, qty, pid, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect("/farmer/profile")

    conn.close()
    return render_template("farmer/edit.html", product=product)
@app.route("/farmer/delete/<int:pid>")
def farmer_delete_product(pid):
    if session.get("role") != "farmer":
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s AND farmer_id=%s", (pid, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/farmer/profile")

# ---------------- BUYER ----------------
@app.route("/marketplace")
def marketplace():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE approved=1")
    products = cur.fetchall()
    conn.close()

    # farmer price + 20% profit
    for p in products:
        p["market_price"] = round(p["price"] * 1.2, 2)

    return render_template("buyer/marketplace.html", products=products)

@app.route("/cart")
def view_cart():
    items = session.get("cart", [])
    total = sum(i["price"] * i["qty"] for i in items)
    return render_template("buyer/cart.html", items=items, total=total)

@app.route("/cart/add/<int:pid>")
def add_to_cart(pid):
    if "cart" not in session:
        session["cart"] = []

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
    product = cur.fetchone()
    conn.close()

    if product:
        found = False
        for item in session["cart"]:
            if item["id"] == product["id"]:
                item["qty"] += 1
                found = True
                break
        if not found:
            session["cart"].append({
                "id": product["id"],
                "name": product["name"],
                "price": round(product["price"] * 1.2, 2),  # marketplace price
                "qty": 1
            })

    session.modified = True   # 🔑 নিশ্চিত করো session update হচ্ছে
    return redirect("/cart")

@app.route("/cart/remove/<int:pid>")
def remove_from_cart(pid):
    if "cart" in session:
        session["cart"] = [i for i in session["cart"] if i["id"] != pid]
    return redirect("/cart")

@app.route("/checkout")
def checkout():
    items = session.get("cart", [])
    total = sum(i["price"] * i["qty"] for i in items)
    return render_template("buyer/checkout.html", items=items, total=total)

@app.route("/payment", methods=["POST"])
def payment():
    method = request.form.get("payment")
    items = session.get("cart", [])
    total = sum(i["price"] * i["qty"] for i in items)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders(user_id, total, payment_method, status)
        VALUES (%s, %s, %s, %s) RETURNING id
    """, (session["user_id"], total, method, "Pending"))
    order_id = cur.fetchone()["id"]

    for i in items:
        cur.execute("""
            INSERT INTO order_items(order_id, product_id, qty, price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, i["id"], i["qty"], i["price"]))

    conn.commit()
    conn.close()

    session["cart"] = []
    return redirect(f"/invoice/{order_id}")

@app.route("/orders")
def orders():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE user_id=%s", (session["user_id"],))
    orders = cur.fetchall()
    conn.close()
    return render_template("buyer/orders.html", orders=orders)

@app.route("/invoice/<int:order_id>")
def invoice(order_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cur.fetchone()
    cur.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    items = cur.fetchall()
    conn.close()
    return render_template("buyer/invoice.html", order=order, items=items)
@app.route("/admin/approve/<int:pid>")
def approve_product(pid):
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE products SET approved=1 WHERE id=%s", (pid,))
    conn.commit()
    conn.close()

    return redirect("/admin/products")
# ---------------- ADMIN ----------------
@app.route("/admin")
def admin_dashboard():
    return render_template("admin/dashboard.html")
@app.route("/admin/products")
def admin_products():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    conn.close()
    return render_template("admin/products.html", products=products)

@app.route("/admin/profit")
def admin_profit():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT SUM(total) AS revenue FROM orders")
    revenue = cur.fetchone()["revenue"] or 0
    farmer_share = round(revenue * 0.8, 2)
    profit = round(revenue * 0.2, 2)
    conn.close()
    return render_template("admin/profit.html", revenue=revenue, farmer=farmer_share, profit=profit)

# ---------------- COURIER ----------------
@app.route("/courier")
def courier_dashboard():
    return render_template("courier/dashboard.html")
@app.route("/meet-team")
def meet_team():
    return render_template("meet_team.html")

if __name__ == "__main__":
    app.run()
