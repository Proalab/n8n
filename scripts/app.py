from quart import Quart, jsonify, request
import subprocess

app = Quart(__name__)

# https://github.com/unclecode/crawl4ai
@app.route('/crawl4ai', methods=['POST'])
async def run_script():
    # Extract optional arguments (e.g., for dynamic script input)
    data = await request.get_json()
    script_args = data.get("args", [])
    try:
        # Run the script asynchronously and capture the output
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