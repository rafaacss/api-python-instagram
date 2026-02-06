import json
import os
import re
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

RESULTS_DIR = Path("/app/results")
RESULTS_DIR.mkdir(exist_ok=True)

K6_SCRIPT = "/app/k6/benchmark.js"


def parse_k6_progress(line):
    """Parse k6 stderr progress lines into structured data."""
    # k6 outputs progress like: running (0m30s), 10/10 VUs, 285 complete and 0 interrupted
    progress_match = re.search(
        r"running \((\dm\d+s)\),\s+(\d+)/(\d+) VUs,\s+(\d+) complete", line
    )
    if progress_match:
        return {
            "elapsed": progress_match.group(1),
            "active_vus": int(progress_match.group(2)),
            "total_vus": int(progress_match.group(3)),
            "iterations": int(progress_match.group(4)),
        }
    return None


def run_k6_test_streaming(test_id, config, sid=None, label=""):
    """Execute k6 test with real-time log streaming via WebSocket."""
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

    cmd = ["k6", "run", K6_SCRIPT]

    try:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stderr_lines = []
        stdout_data = []

        def read_stderr():
            for line in proc.stderr:
                line = line.strip()
                if not line:
                    continue
                stderr_lines.append(line)
                if sid:
                    progress = parse_k6_progress(line)
                    socketio.emit(
                        "log",
                        {
                            "test_id": test_id,
                            "label": label,
                            "line": line,
                            "progress": progress,
                        },
                        to=sid,
                    )

        t = threading.Thread(target=read_stderr, daemon=True)
        t.start()

        stdout_raw = proc.stdout.read()
        stdout_data.append(stdout_raw)

        proc.wait(timeout=600)
        t.join(timeout=5)

        output = stdout_data[0].strip() if stdout_data else ""

        try:
            summary = json.loads(output)
        except json.JSONDecodeError:
            summary = {"raw_output": output, "stderr": "\n".join(stderr_lines)}

        summary["test_id"] = test_id
        summary["timestamp"] = datetime.now().isoformat()
        summary["config"] = {
            k: v for k, v in config.items() if k not in ("login_pass",)
        }

        result_file = RESULTS_DIR / f"{test_id}.json"
        with open(result_file, "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    except subprocess.TimeoutExpired:
        proc.kill()
        return {"error": "Test timed out (max 10 minutes)", "test_id": test_id}
    except Exception as e:
        return {"error": str(e), "test_id": test_id}


def run_k6_test(test_id, config):
    """Execute k6 test (non-streaming for REST API)."""
    return run_k6_test_streaming(test_id, config)


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
    p9074 = safe_get(m74, "http_req_duration", "p90")
    p9085 = safe_get(m85, "http_req_duration", "p90")
    p9574 = safe_get(m74, "http_req_duration", "p95")
    p9585 = safe_get(m85, "http_req_duration", "p95")
    med74 = safe_get(m74, "http_req_duration", "med")
    med85 = safe_get(m85, "http_req_duration", "med")
    min74 = safe_get(m74, "http_req_duration", "min")
    min85 = safe_get(m85, "http_req_duration", "min")
    max74 = safe_get(m74, "http_req_duration", "max")
    max85 = safe_get(m85, "http_req_duration", "max")
    rps74 = safe_get(m74, "http_reqs", "rate")
    rps85 = safe_get(m85, "http_reqs", "rate")
    reqs74 = safe_get(m74, "http_reqs", "count")
    reqs85 = safe_get(m85, "http_reqs", "count")
    fail74 = safe_get(m74, "http_req_failed", "rate")
    fail85 = safe_get(m85, "http_req_failed", "rate")
    iter74 = safe_get(m74, "iterations", "count")
    iter85 = safe_get(m85, "iterations", "count")
    iterr74 = safe_get(m74, "iterations", "rate")
    iterr85 = safe_get(m85, "iterations", "rate")

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
            "median_response_ms": {
                "php74": round(med74, 2),
                "php85": round(med85, 2),
                "diff_percent": calc_diff(med74, med85),
                "winner": "PHP 8.5" if med85 < med74 else "PHP 7.4",
            },
            "p90_response_ms": {
                "php74": round(p9074, 2),
                "php85": round(p9085, 2),
                "diff_percent": calc_diff(p9074, p9085),
                "winner": "PHP 8.5" if p9085 < p9074 else "PHP 7.4",
            },
            "p95_response_ms": {
                "php74": round(p9574, 2),
                "php85": round(p9585, 2),
                "diff_percent": calc_diff(p9574, p9585),
                "winner": "PHP 8.5" if p9585 < p9574 else "PHP 7.4",
            },
            "min_response_ms": {
                "php74": round(min74, 2),
                "php85": round(min85, 2),
                "diff_percent": calc_diff(min74, min85),
                "winner": "PHP 8.5" if min85 < min74 else "PHP 7.4",
            },
            "max_response_ms": {
                "php74": round(max74, 2),
                "php85": round(max85, 2),
                "diff_percent": calc_diff(max74, max85),
                "winner": "PHP 8.5" if max85 < max74 else "PHP 7.4",
            },
            "requests_per_sec": {
                "php74": round(rps74, 2),
                "php85": round(rps85, 2),
                "diff_percent": calc_diff(rps74, rps85),
                "winner": "PHP 8.5" if rps85 > rps74 else "PHP 7.4",
            },
            "total_requests": {
                "php74": reqs74,
                "php85": reqs85,
                "diff_percent": calc_diff(reqs74, reqs85),
                "winner": "PHP 8.5" if reqs85 > reqs74 else "PHP 7.4",
            },
            "error_rate": {
                "php74": round(fail74 * 100, 2),
                "php85": round(fail85 * 100, 2),
                "diff_percent": calc_diff(fail74, fail85) if fail74 > 0 else 0,
                "winner": "PHP 8.5" if fail85 <= fail74 else "PHP 7.4",
            },
            "iterations": {
                "php74": iter74,
                "php85": iter85,
                "diff_percent": calc_diff(iter74, iter85),
                "winner": "PHP 8.5" if iter85 > iter74 else "PHP 7.4",
            },
            "iterations_per_sec": {
                "php74": round(iterr74, 2),
                "php85": round(iterr85, 2),
                "diff_percent": calc_diff(iterr74, iterr85),
                "winner": "PHP 8.5" if iterr85 > iterr74 else "PHP 7.4",
            },
        },
    }


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/test", methods=["POST"])
def start_test():
    config = request.json
    if not config or not config.get("target_url"):
        return jsonify({"error": "target_url is required"}), 400

    test_id = str(uuid.uuid4())[:8]
    result = run_k6_test(test_id, config)
    return jsonify(result)


@app.route("/api/compare", methods=["POST"])
def compare_test():
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

    config_74 = {**base_config, "target_url": data["url_php74"]}
    result_74 = run_k6_test(f"{compare_id}-php74", config_74)

    config_85 = {**base_config, "target_url": data["url_php85"]}
    result_85 = run_k6_test(f"{compare_id}-php85", config_85)

    comparison = build_comparison(result_74, result_85, data)
    comparison["compare_id"] = compare_id
    comparison["timestamp"] = datetime.now().isoformat()

    result_file = RESULTS_DIR / f"compare-{compare_id}.json"
    with open(result_file, "w") as f:
        json.dump(comparison, f, indent=2)

    return jsonify(comparison)


@app.route("/api/results", methods=["GET"])
def list_results():
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
                        "config": data.get("config", {}),
                    }
                )
        except Exception:
            pass
    return jsonify(results)


@app.route("/api/results/<filename>", methods=["GET"])
def get_result(filename):
    result_file = RESULTS_DIR / filename
    if not result_file.exists():
        return jsonify({"error": "not found"}), 404
    with open(result_file) as f:
        return jsonify(json.load(f))


@app.route("/api/results/<filename>", methods=["DELETE"])
def delete_result(filename):
    result_file = RESULTS_DIR / filename
    if not result_file.exists():
        return jsonify({"error": "not found"}), 404
    result_file.unlink()
    return jsonify({"status": "deleted"})


# WebSocket handlers
@socketio.on("run_compare")
def handle_compare(data):
    sid = request.sid
    emit("status", {"message": "Iniciando teste PHP 7.4...", "phase": "php74", "percent": 5})

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

    emit("status", {"message": "Executando k6 em PHP 7.4...", "phase": "php74", "percent": 10})
    config_74 = {**base_config, "target_url": data["url_php74"]}
    result_74 = run_k6_test_streaming(f"{compare_id}-php74", config_74, sid=sid, label="PHP 7.4")

    emit("status", {
        "message": "PHP 7.4 concluido! Iniciando PHP 8.5...",
        "phase": "php85",
        "percent": 50,
        "result_74": result_74,
    })

    config_85 = {**base_config, "target_url": data["url_php85"]}
    result_85 = run_k6_test_streaming(f"{compare_id}-php85", config_85, sid=sid, label="PHP 8.5")

    emit("status", {"message": "PHP 8.5 concluido! Gerando relatorio...", "phase": "done", "percent": 95})

    comparison = build_comparison(result_74, result_85, data)
    comparison["compare_id"] = compare_id
    comparison["timestamp"] = datetime.now().isoformat()

    result_file = RESULTS_DIR / f"compare-{compare_id}.json"
    with open(result_file, "w") as f:
        json.dump(comparison, f, indent=2)

    emit("result", comparison)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
