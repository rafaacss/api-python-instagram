import json
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

RESULTS_DIR = Path("/app/results")
RESULTS_DIR.mkdir(exist_ok=True)

K6_SCRIPT = "/app/k6/benchmark.js"

# Store running tests
running_tests = {}


def run_k6_test(test_id, config):
    """Execute k6 test and stream progress via WebSocket."""
    env = os.environ.copy()
    env["TARGET_URL"] = config["target_url"]
    env["TEST_TYPE"] = config.get("test_type", "homepage")
    env["VUS"] = str(config.get("vus", 10))
    env["DURATION"] = config.get("duration", "30s")
    env["SLEEP"] = str(config.get("sleep", 0.5))

    if config.get("endpoints"):
        env["ENDPOINTS"] = config["endpoints"]

    if config.get("login_url"):
        env["LOGIN_URL"] = config["login_url"]
        env["LOGIN_USER"] = config.get("login_user", "")
        env["LOGIN_PASS"] = config.get("login_pass", "")
        env["LOGIN_USER_FIELD"] = config.get("login_user_field", "email")
        env["LOGIN_PASS_FIELD"] = config.get("login_pass_field", "password")

    cmd = ["k6", "run", "--quiet", K6_SCRIPT]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )

        output = result.stdout.strip()

        # Try to parse JSON summary from k6
        try:
            summary = json.loads(output)
        except json.JSONDecodeError:
            summary = {"raw_output": output, "stderr": result.stderr}

        summary["test_id"] = test_id
        summary["timestamp"] = datetime.now().isoformat()
        summary["config"] = {
            k: v for k, v in config.items() if k not in ("login_pass",)
        }

        # Save result
        result_file = RESULTS_DIR / f"{test_id}.json"
        with open(result_file, "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    except subprocess.TimeoutExpired:
        return {"error": "Test timed out (max 10 minutes)", "test_id": test_id}
    except Exception as e:
        return {"error": str(e), "test_id": test_id}


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/test", methods=["POST"])
def start_test():
    """Start a single benchmark test."""
    config = request.json
    if not config or not config.get("target_url"):
        return jsonify({"error": "target_url is required"}), 400

    test_id = str(uuid.uuid4())[:8]
    result = run_k6_test(test_id, config)
    return jsonify(result)


@app.route("/api/compare", methods=["POST"])
def compare_test():
    """Run benchmark on two URLs and compare."""
    data = request.json
    if not data or not data.get("url_php74") or not data.get("url_php85"):
        return jsonify({"error": "url_php74 and url_php85 are required"}), 400

    base_config = {
        "test_type": data.get("test_type", "homepage"),
        "vus": data.get("vus", 10),
        "duration": data.get("duration", "30s"),
        "endpoints": data.get("endpoints", ""),
        "sleep": data.get("sleep", 0.5),
        "login_url": data.get("login_url", ""),
        "login_user": data.get("login_user", ""),
        "login_pass": data.get("login_pass", ""),
        "login_user_field": data.get("login_user_field", "email"),
        "login_pass_field": data.get("login_pass_field", "password"),
    }

    compare_id = str(uuid.uuid4())[:8]

    # Run PHP 7.4 test
    config_74 = {**base_config, "target_url": data["url_php74"]}
    result_74 = run_k6_test(f"{compare_id}-php74", config_74)

    # Run PHP 8.5 test
    config_85 = {**base_config, "target_url": data["url_php85"]}
    result_85 = run_k6_test(f"{compare_id}-php85", config_85)

    # Build comparison
    comparison = build_comparison(result_74, result_85, data)
    comparison["compare_id"] = compare_id
    comparison["timestamp"] = datetime.now().isoformat()

    # Save comparison
    result_file = RESULTS_DIR / f"compare-{compare_id}.json"
    with open(result_file, "w") as f:
        json.dump(comparison, f, indent=2)

    return jsonify(comparison)


def build_comparison(r74, r85, config):
    """Build a comparison object between two test results."""
    m74 = r74.get("metrics", {})
    m85 = r85.get("metrics", {})

    def safe_get(metrics, *keys):
        val = metrics
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k, 0)
            else:
                return 0
        return val or 0

    def calc_diff(v74, v85):
        if v74 == 0:
            return 0
        return round(((v85 - v74) / v74) * 100, 2)

    avg74 = safe_get(m74, "http_req_duration", "avg")
    avg85 = safe_get(m85, "http_req_duration", "avg")
    p9574 = safe_get(m74, "http_req_duration", "p95")
    p9585 = safe_get(m85, "http_req_duration", "p95")
    rps74 = safe_get(m74, "http_reqs", "rate")
    rps85 = safe_get(m85, "http_reqs", "rate")

    return {
        "config": {
            "url_php74": config.get("url_php74"),
            "url_php85": config.get("url_php85"),
            "test_type": config.get("test_type"),
            "vus": config.get("vus"),
            "duration": config.get("duration"),
        },
        "php74": r74,
        "php85": r85,
        "summary": {
            "avg_response_ms": {
                "php74": round(avg74, 2),
                "php85": round(avg85, 2),
                "diff_percent": calc_diff(avg74, avg85),
                "winner": "PHP 8.5" if avg85 < avg74 else "PHP 7.4",
            },
            "p95_response_ms": {
                "php74": round(p9574, 2),
                "php85": round(p9585, 2),
                "diff_percent": calc_diff(p9574, p9585),
                "winner": "PHP 8.5" if p9585 < p9574 else "PHP 7.4",
            },
            "requests_per_sec": {
                "php74": round(rps74, 2),
                "php85": round(rps85, 2),
                "diff_percent": calc_diff(rps74, rps85),
                "winner": "PHP 8.5" if rps85 > rps74 else "PHP 7.4",
            },
        },
    }


@app.route("/api/results", methods=["GET"])
def list_results():
    """List all saved results."""
    results = []
    for f in sorted(RESULTS_DIR.glob("*.json"), reverse=True):
        try:
            with open(f) as fh:
                data = json.load(fh)
                results.append(
                    {
                        "filename": f.name,
                        "timestamp": data.get("timestamp", ""),
                        "compare_id": data.get("compare_id", ""),
                        "test_id": data.get("test_id", ""),
                    }
                )
        except Exception:
            pass
    return jsonify(results)


@app.route("/api/results/<filename>", methods=["GET"])
def get_result(filename):
    """Get a specific result file."""
    result_file = RESULTS_DIR / filename
    if not result_file.exists():
        return jsonify({"error": "not found"}), 404
    with open(result_file) as f:
        return jsonify(json.load(f))


# WebSocket for real-time test execution
@socketio.on("run_compare")
def handle_compare(data):
    emit("status", {"message": "Iniciando teste PHP 7.4...", "phase": "php74"})

    base_config = {
        "test_type": data.get("test_type", "homepage"),
        "vus": data.get("vus", 10),
        "duration": data.get("duration", "30s"),
        "endpoints": data.get("endpoints", ""),
        "sleep": data.get("sleep", 0.5),
        "login_url": data.get("login_url", ""),
        "login_user": data.get("login_user", ""),
        "login_pass": data.get("login_pass", ""),
        "login_user_field": data.get("login_user_field", "email"),
        "login_pass_field": data.get("login_pass_field", "password"),
    }

    compare_id = str(uuid.uuid4())[:8]

    config_74 = {**base_config, "target_url": data["url_php74"]}
    result_74 = run_k6_test(f"{compare_id}-php74", config_74)
    emit("status", {"message": "PHP 7.4 concluído! Iniciando PHP 8.5...", "phase": "php85", "result_74": result_74})

    config_85 = {**base_config, "target_url": data["url_php85"]}
    result_85 = run_k6_test(f"{compare_id}-php85", config_85)
    emit("status", {"message": "PHP 8.5 concluído! Gerando comparação...", "phase": "done"})

    comparison = build_comparison(result_74, result_85, data)
    comparison["compare_id"] = compare_id
    comparison["timestamp"] = datetime.now().isoformat()

    result_file = RESULTS_DIR / f"compare-{compare_id}.json"
    with open(result_file, "w") as f:
        json.dump(comparison, f, indent=2)

    emit("result", comparison)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
