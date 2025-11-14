from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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

# Admin login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            login_user(User(username))
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

# Dynamic dashboard with optional table switch
@app.route("/dashboard", methods=["GET", "POST"])
@app.route("/dashboard/<table_name>", methods=["GET", "POST"])
@login_required
def dashboard(table_name="users"):
    # Handle form submission
    if request.method == "POST":
        table_name = request.form.get("table_name")
        return redirect(url_for("dashboard", table_name=table_name))

    # Fetch table data from Supabase
    try:
        response = supabase.table(table_name).select("*").execute()
        table_data = response.data
    except Exception:
        table_data = None
        flash(f"Table '{table_name}' does not exist!", "danger")

    return render_template("dashboard.html", table_name=table_name, table_data=table_data)

# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
