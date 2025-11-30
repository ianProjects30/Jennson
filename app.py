from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.middleware.proxy_fix import ProxyFix # Import ProxyFix
# Assuming 'supabase_client' is a module you created
from supabase_client import supabase 
import pandas as pd
from io import BytesIO

# -------------------------------------
# Flask App Setup
# -------------------------------------

app = Flask(__name__)
# Apply ProxyFix to handle headers from Render's reverse proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
) 
app.secret_key = "supersecretkey"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# -------------------------------------
# User Model and Login Logic
# -------------------------------------

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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


# -------------------------------------
# Dashboard and CRUD Logic
# -------------------------------------

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    try:
        tables_resp = supabase.rpc("get_tables").execute()
        # Filter out system tables if necessary, though 'users' is kept as example
        tables_list = [t["table_name"] for t in tables_resp.data if t["table_name"] != 'users']
    except Exception as e:
        # Fallback if RPC or Supabase connection fails
        tables_list = ["sample_table"] 
        # print(f"Supabase error fetching tables: {e}") 

    # Ensure tables_list is not empty if fallback is used
    if not tables_list:
        tables_list = ["sample_table"]
        
    table_name = request.args.get("table") or tables_list[0]

    if request.method == "POST":
        action = request.form.get("action")
        row_id = request.form.get("row_id")

        try:
            if action == "delete":
                supabase.table(table_name).delete().eq("id", int(row_id)).execute()
                flash(f"Row {row_id} deleted.", "success")

            elif action == "update":
                # Ensure 'id' is not in updates dictionary, as it's used for the .eq() filter
                updates = {k: v for k, v in request.form.items() if k not in ["action", "row_id", "id"]}
                supabase.table(table_name).update(updates).eq("id", int(row_id)).execute()
                flash(f"Row {row_id} updated.", "success")

            elif action == "add":
                data = {k: v for k, v in request.form.items() if k != "action" and k != "id"}
                supabase.table(table_name).insert(data).execute()
                flash("New row added.", "success")
        except Exception as e:
            flash(f"Database operation failed: {e}", "danger")

        return redirect(url_for("dashboard", table=table_name))

    try:
        # Fetch data for display
        response = supabase.table(table_name).select("*").execute()
        table_data = response.data
    except:
        table_data = []
        flash(f"Could not load data for table '{table_name}'.", "danger")

    return render_template(
        "dashboard.html",
        table_name=table_name,
        tables_list=tables_list,
        table_data=table_data,
    )

# -------------------------------------
# Export Logic
# -------------------------------------

# Export ALL data (existing function)
@app.route("/export_excel")
@login_required
def export_excel():
    # ... (Your original export_excel function logic remains the same) ...
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

# Export FILTERED data (corrected to use GET/Server-Side Filtering)
@app.route("/export_excel_filtered_manual", methods=["GET"])
@login_required
def export_excel_filtered_manual():
    table_name = request.args.get("table")
    
    # Get filter criteria from URL query parameters (sent by JS)
    col_index_str = request.args.get("filter_col_index")
    search_val = request.args.get("filter_search_value", "").strip().lower()

    # 1. Fetch ALL data from Supabase
    response = supabase.table(table_name).select("*").execute()
    table_data = response.data
    
    if not table_data:
        flash("No data to export!", "warning")
        return redirect(url_for("dashboard", table=table_name))

    df = pd.DataFrame(table_data)
    
    # 2. Server-side filtering logic
    if search_val and col_index_str is not None:
        try:
            col_index = int(col_index_str)
            # Find the column name using the index
            column_name = df.columns[col_index]
            
            # Filter the DataFrame based on the search value
            df = df[df[column_name].astype(str).str.lower().str.contains(search_val, na=False)]
            
        except (IndexError, ValueError) as e:
            # This catches errors if the column index is out of bounds or not an integer
            flash(f"Filter error during export: {e}", "warning")

    if df.empty:
        flash("No rows match your filter to export.", "warning")
        return redirect(url_for("dashboard", table=table_name))

    # 3. Excel Generation
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


if __name__ == "__main__":
    app.run(debug=True)