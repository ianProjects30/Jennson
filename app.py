from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from supabase_client import supabase

app = Flask(__name__)
app.secret_key = "supersecretkey"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_USERNAME:
        return User(user_id)
    return None

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            login_user(User(username))
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

# Dashboard with dynamic table selection and CRUD
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    # Get table list
    try:
        tables_resp = supabase.rpc("get_tables").execute()
        tables_list = [t['table_name'] for t in tables_resp.data]
    except:
        tables_list = ["users"]

    # Get selected table
    table_name = request.args.get("table") or tables_list[0]

    # Handle CRUD actions
    if request.method == "POST":
        action = request.form.get("action")
        row_id = request.form.get("row_id")

        if action == "delete":
            supabase.table(table_name).delete().eq("id", int(row_id)).execute()
            flash(f"Row ID {row_id} deleted from {table_name}.", "success")

        elif action == "update":
            updates = {k: v for k, v in request.form.items() if k not in ["action", "row_id"]}
            supabase.table(table_name).update(updates).eq("id", int(row_id)).execute()
            flash(f"Row ID {row_id} updated.", "success")

        elif action == "add":
            new_data = {k: v for k, v in request.form.items() if k != "action"}
            supabase.table(table_name).insert(new_data).execute()
            flash("New row added.", "success")

        return redirect(url_for("dashboard", table=table_name))

    # Fetch table data
    try:
        response = supabase.table(table_name).select("*").execute()
        table_data = response.data
    except Exception:
        table_data = []
        flash(f"Table '{table_name}' does not exist!", "danger")

    return render_template(
        "dashboard.html",
        table_name=table_name,
        table_data=table_data,
        tables_list=tables_list
    )

# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
