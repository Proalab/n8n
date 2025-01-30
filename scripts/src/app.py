from quart import Quart, jsonify, request
import subprocess
import json

app = Quart(__name__)

# JWT Generation Route via subprocess
@app.route('/generate-apple-jwt', methods=['GET'])
async def generate_jwt_route():
    try:
        result = subprocess.run(
            ["python", "/app/scripts/apple-jwt/generate-token.py"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            token_data = json.loads(result.stdout.strip())  # Parse JSON output
            return jsonify({"status": "success", "token": token_data["token"]})
        else:
            return jsonify({"status": "error", "message": result.stderr}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Existing script execution route
@app.route('/crawl4ai', methods=['POST'])
async def run_script():
    data = await request.get_json()
    script_args = data.get("args", [])
    
    try:
        result = subprocess.run(
            ["python", "/app/scripts/crawl4ai/3-crawl-fast.py"] + script_args,
            capture_output=True,
            text=True
        )
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        })
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)