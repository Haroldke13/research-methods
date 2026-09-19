from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from qrmf.analysis import run_analysis


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "local-development-only-change-me"),
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        OUTPUT_DIR=ROOT / "outputs",
        RUNTIME_DIR=ROOT / "runtime",
        DEMO_DATA=ROOT / "data" / "demo_study.csv",
        DEMO_SPEC=ROOT / "data" / "demo_study_spec.json",
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["OUTPUT_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["RUNTIME_DIR"]).mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        results = _load_json(Path(app.config["OUTPUT_DIR"]) / "analysis_results.json")
        return render_template("index.html", results=results)

    @app.post("/run-demo")
    def run_demo():
        try:
            run_analysis(
                app.config["DEMO_DATA"],
                app.config["DEMO_SPEC"],
                app.config["OUTPUT_DIR"],
            )
            flash("Demo analysis completed from the bundled synthetic dataset.", "success")
        except Exception as exc:
            app.logger.exception("Demo analysis failed")
            flash(f"Analysis failed: {exc}", "error")
        return redirect(url_for("index"))

    @app.route("/analyze", methods=["GET", "POST"])
    def analyze():
        if request.method == "GET":
            example_spec = Path(app.config["DEMO_SPEC"]).read_text(encoding="utf-8")
            return render_template("analyze.html", example_spec=example_spec)

        data_file = request.files.get("data_file")
        spec_text = request.form.get("spec_json", "").strip()
        if not data_file or not data_file.filename:
            flash("Choose a CSV file.", "error")
            return redirect(url_for("analyze"))
        if Path(secure_filename(data_file.filename)).suffix.lower() != ".csv":
            flash("Only CSV input is accepted.", "error")
            return redirect(url_for("analyze"))
        try:
            spec = json.loads(spec_text)
        except json.JSONDecodeError as exc:
            flash(f"Study specification is not valid JSON: {exc}", "error")
            return redirect(url_for("analyze"))

        run_id = uuid.uuid4().hex[:12]
        run_dir = Path(app.config["RUNTIME_DIR"]) / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        input_path = run_dir / "input.csv"
        output_dir = run_dir / "outputs"
        data_file.save(input_path)
        (run_dir / "study_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

        try:
            result = run_analysis(input_path, spec, output_dir)
        except Exception as exc:
            shutil.rmtree(run_dir, ignore_errors=True)
            app.logger.exception("Uploaded analysis failed")
            flash(f"Analysis failed validation or execution: {exc}", "error")
            return redirect(url_for("analyze"))

        return render_template("run_result.html", run_id=run_id, results=result)

    @app.get("/run/<run_id>/download/<path:name>")
    def download_run(run_id: str, name: str):
        if not run_id.isalnum() or len(run_id) > 32:
            abort(404)
        run_output = Path(app.config["RUNTIME_DIR"]) / run_id / "outputs"
        allowed = {"analysis_results.json", "analysis_report.md", "analysis_summary.csv"}
        if name not in allowed or not (run_output / name).is_file():
            abort(404)
        return send_from_directory(run_output, name, as_attachment=True)

    @app.post("/run/<run_id>/delete")
    def delete_run(run_id: str):
        if not run_id.isalnum() or len(run_id) > 32:
            abort(404)
        run_dir = Path(app.config["RUNTIME_DIR"]) / run_id
        if run_dir.exists() and run_dir.parent.resolve() == Path(app.config["RUNTIME_DIR"]).resolve():
            shutil.rmtree(run_dir)
        flash("Temporary run data deleted.", "success")
        return redirect(url_for("index"))

    @app.get("/figure/<name>")
    def figure(name: str):
        allowed = {"outcome_by_group.png"}
        if name not in allowed:
            abort(404)
        figure_dir = Path(app.config["OUTPUT_DIR"]) / "figures"
        if not (figure_dir / name).is_file():
            abort(404)
        return send_from_directory(figure_dir, name)

    @app.get("/download/<name>")
    def download_output(name: str):
        allowed = {"analysis_results.json", "analysis_report.md", "analysis_summary.csv"}
        if name not in allowed:
            abort(404)
        output_dir = Path(app.config["OUTPUT_DIR"])
        if not (output_dir / name).is_file():
            abort(404)
        return send_from_directory(output_dir, name, as_attachment=True)

    @app.get("/api/results")
    def api_results():
        result = _load_json(Path(app.config["OUTPUT_DIR"]) / "analysis_results.json")
        if not result:
            return jsonify({"status": "empty", "message": "Run the demo analysis first."}), 404
        return jsonify(result)

    @app.errorhandler(413)
    def too_large(_exc):
        return render_template("error.html", title="Upload too large", message="The uploaded file exceeds MAX_UPLOAD_MB."), 413

    @app.errorhandler(404)
    def not_found(_exc):
        return render_template("error.html", title="Not found", message="The requested resource does not exist."), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_ENV") == "development")