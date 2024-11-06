import json
import openai
from flask_cors import CORS
from flask import Flask, jsonify
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/analyze": {"origins": "http://localhost:3000"}
})

openai.api_key = f'MY_KEY_PLACEHOLDER'

def load_json_data(file_path):
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        app.logger.error(f"File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        app.logger.error(f"Invalid JSON format in file: {file_path}")
        return {}

patents_data = load_json_data('patents.json')
company_products_data = load_json_data('company_products.json')

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error."}), 500

@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f"Not found error: {error}")
    return jsonify({"error": "Resource not found."}), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    app.logger.error(f"Method not allowed error: {error}")
    return jsonify({"error": "Method not allowed."}), 405

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
