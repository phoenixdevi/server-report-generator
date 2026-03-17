#!/usr/bin/env python3
"""
app.py
------
The Flask web server.  This is the entry point for the containerised app.

It exposes two HTTP endpoints:
  GET  /           → serves the browser UI (index.html)
  POST /generate   → accepts JSON, builds the Excel report, returns it as a download

All the actual report logic lives in report_builder.py.
This file is intentionally thin — it only handles HTTP concerns:
  - parsing and validating the incoming request
  - calling build_report()
  - returning either the .xlsx file or a JSON error response
"""

import io
import json
from flask import Flask, request, send_file, render_template, jsonify
from report_builder import build_report
from ai_service import extract_data_from_images
import database

# Initialise Database
database.init_db()

# Initialise Flask.
# __name__ tells Flask where to look for the templates/ folder
# (it looks in the same directory as this file).
app = Flask(__name__)


# ─────────────────────────────────────────────
# ROUTE: GET /
# ─────────────────────────────────────────────
@app.route("/")
def index():
    """
    Serve the main web page.
    Flask looks for 'index.html' in the templates/ folder automatically.
    """
    return render_template("index.html")


# ─────────────────────────────────────────────
# ROUTE: POST /generate
# ─────────────────────────────────────────────
@app.route("/generate", methods=["POST"])
def generate():
    """
    Accept a JSON payload from the browser and return a generated Excel file.

    Expected request body (JSON):
    {
        "data": {
            "one_day": [ ... ],        // server metric entries for the full period
            "under_utilized": [ ... ]  // low-usage server entries
        },
        "report_date":  "23rd October",  // used in the report title and filename
        "shift":        "Day",           // "Day" or "Night"
        "auto_add_new": true             // whether to auto-add unknown servers to master
    }

    Success response:
        HTTP 200 with the .xlsx file as an attachment (triggers browser download)

    Error responses:
        HTTP 400 — invalid or missing input fields
        HTTP 500 — report generation failed (details in JSON body)
    """

    # Parse the JSON body. force=True means we don't require the Content-Type header
    # to be exactly "application/json" (more forgiving for browser fetch calls).
    # silent=True means it returns None instead of raising an error on bad JSON.
    payload = request.get_json(force=True, silent=True)

    if not payload:
        # Body was empty or completely unparseable as JSON
        return jsonify({"error": "Invalid or empty request body."}), 400

    # Extract and sanitise individual fields
    data         = payload.get("data")                          # the server metrics dict
    report_date  = (payload.get("report_date") or "").strip()  # e.g. "23rd October"
    shift        = (payload.get("shift")       or "").strip()  # "Day" or "Night"
    author       = (payload.get("author")      or "").strip()  # Support Engineer name
    auto_add_new = bool(payload.get("auto_add_new", True))     # default: auto-add on

    # ── Input validation ──────────────────────────────────────────────────────
    if not isinstance(data, dict):
        # The AI chatbot output must have been wrapped under the "data" key by the frontend
        return jsonify({"error": "Field 'data' must be the parsed JSON object."}), 400
    if not report_date:
        return jsonify({"error": "report_date is required."}), 400
    if not shift:
        return jsonify({"error": "shift is required."}), 400

    # ── Report generation ─────────────────────────────────────────────────────
    try:
        # build_report() returns:
        #   xlsx_bytes : raw bytes of the finished .xlsx file
        #   filename   : suggested download name, e.g. "Server_Report_23Oct.xlsx"
        #   log        : dict of what was matched/added/skipped (already written to disk)
        xlsx_bytes, filename, log = build_report(data, report_date, shift, auto_add_new, author)
    except Exception as e:
        # Something went wrong inside the report builder — tell the browser clearly.
        # The full traceback has already been written to the run log on disk.
        return jsonify({"error": str(e)}), 500

    # ── Send the file ─────────────────────────────────────────────────────────
    # Wrap the bytes in a BytesIO buffer so send_file can read from it like a file.
    # as_attachment=True adds: Content-Disposition: attachment; filename="..."
    # which makes the browser prompt a download rather than trying to display it.
    return send_file(
        io.BytesIO(xlsx_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ─────────────────────────────────────────────
# ROUTE: POST /extract
# ─────────────────────────────────────────────
@app.route("/extract", methods=["POST"])
def extract():
    """
    Accept image files, send them to the AI service, and return extracted JSON.
    """
    if 'files' not in request.files:
        return jsonify({"error": "No files provided."}), 400
    
    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "No files selected."}), 400

    try:
        # Fetch the active AI configuration from the database
        config = database.get_active_config()
        if not config:
            return jsonify({"error": "No active AI configuration found. Please add one in settings."}), 400

        image_bytes_list = [f.read() for f in files]
        # Perform AI Extraction using the stored config
        extracted_json = extract_data_from_images(image_bytes_list, config)
        # Return with insertion order preserved (name first, like Claude)
        return app.response_class(
            response=json.dumps(extracted_json, indent=2, ensure_ascii=False),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# AI CONFIGURATION ENDPOINTS
# ─────────────────────────────────────────────

@app.route("/api/configs", methods=["GET"])
def get_configs():
    """List all saved AI configurations."""
    return jsonify(database.get_configs())

@app.route("/api/configs", methods=["POST"])
def add_config():
    """Save a new AI configuration."""
    data = request.get_json()
    if not all(k in data for k in ("name", "provider", "model_id", "api_key")):
        return jsonify({"error": "Missing required fields."}), 400
    
    success = database.add_config(
        data["name"], data["provider"], data["model_id"], data["api_key"]
    )
    if success:
        return jsonify({"message": "Configuration saved."}), 201
    else:
        return jsonify({"error": "Configuration name already exists."}), 400

@app.route("/api/configs/select", methods=["POST"])
def select_config():
    """Switch to a specific configuration."""
    data = request.get_json()
    config_id = data.get("id")
    if not config_id:
        return jsonify({"error": "No ID provided."}), 400
    
    database.set_active_config(config_id)
    return jsonify({"message": "Configuration selected."})

@app.route("/api/configs/<int:config_id>", methods=["DELETE"])
def delete_config(config_id):
    """Delete a configuration."""
    database.delete_config(config_id)
    return jsonify({"message": "Configuration deleted."})


# ─────────────────────────────────────────────
# LOCAL DEV ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # This block only runs when you execute `python app.py` directly.
    # In Docker, gunicorn is used instead (see Dockerfile CMD), which is
    # more stable and handles concurrent requests better than Flask's
    # built-in dev server.
    app.run(host="0.0.0.0", port=5000, debug=False)
