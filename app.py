from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from supabase_client import supabase
import pandas as pd
from io import BytesIO

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

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():

    try:
        tables_resp = supabase.rpc("get_tables").execute()
        tables_list = [t["table_name"] for t in tables_resp.data]
    except:
        tables_list = ["users"]

    table_name = request.args.get("table") or tables_list[0]

    if request.method == "POST":
        action = request.form.get("action")
        row_id = request.form.get("row_id")

        if action == "delete":
            supabase.table(table_name).delete().eq("id", int(row_id)).execute()
            flash(f"Row {row_id} deleted.", "success")

        elif action == "update":
            updates = {k: v for k, v in request.form.items() if k not in ["action", "row_id"]}
            supabase.table(table_name).update(updates).eq("id", int(row_id)).execute()
            flash(f"Row {row_id} updated.", "success")

        elif action == "add":
            data = {k: v for k, v in request.form.items() if k != "action"}
            supabase.table(table_name).insert(data).execute()
            flash("New row added.", "success")

        return redirect(url_for("dashboard", table=table_name))

    try:
        response = supabase.table(table_name).select("*").execute()
        table_data = response.data
    except:
        table_data = []
        flash("Table not found!", "danger")

    return render_template(
        "dashboard.html",
        table_name=table_name,
        tables_list=tables_list,
        table_data=table_data,
    )


@app.route("/export_excel")
@login_required
def export_excel():
    table_name = request.args.get("table")

    response = supabase.table(table_name).select("*").execute()
    table_data = response.data

    if not table_data:
        flash("No data to export!", "warning")
        return redirect(url_for("dashboard", table=table_name))

    df = pd.DataFrame(table_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=table_name)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"{table_name}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/export_excel_filtered_manual", methods=["POST"])
@login_required
def export_excel_filtered_manual():
    import json

    table_name = request.args.get("table")

    filtered_json = request.form.get("filtered_rows")

    if not filtered_json:
        flash("No filtered data received.", "warning")
        return redirect(url_for("dashboard", table=table_name))

    rows = json.loads(filtered_json)

    if not rows:
        flash("No rows match your filter.", "warning")
        return redirect(url_for("dashboard", table=table_name))

    df = pd.DataFrame(rows)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Filtered")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"{table_name}_filtered_manual.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
