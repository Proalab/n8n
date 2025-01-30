import logging
import datetime
from quart import Quart, jsonify, request
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Quart(__name__)

@app.route('/')
async def index():
    return jsonify({
        "status": "Server is running",
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route('/crawl4ai', methods=['POST'])
async def run_script():
    data = await request.get_json()
    script_args = data.get("args", [])
    timeout = data.get("timeout", 60)
    logger.info("Received request with args=%s and timeout=%s", script_args, timeout)

    try:
        result = subprocess.run(
            ["python", "/app/scripts/crawl4ai/3-crawl-fast.py"] + script_args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        logger.info("Script finished with return code %s", result.returncode)
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        })
    except subprocess.TimeoutExpired:
        logger.error("Script timed out after %s seconds", timeout)
        return jsonify({"status": "error", "error": f"Timeout after {timeout} seconds"}), 504
    except Exception as e:
        logger.error("Script error: %s", str(e))
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)