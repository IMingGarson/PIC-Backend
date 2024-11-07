import json
import os
import uuid
from flask_cors import CORS
from datetime import datetime
from flask import Flask, request, jsonify
from os.path import join, dirname
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from utils.fuzzy_match import fuzzy_match
from utils.openai import extract_relevant_claims, generate_explanation, generate_overall_risk_assessment

app = Flask(__name__)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

is_dev = os.getenv("DEVELOPMENT") == '1'

CORS(app, resources={
    r"/analyze": {"origins": ["http://localhost:3000", "https://patent-infringement-checker.netlify.app"]}
})

limiter = Limiter(
    get_remote_address,
    app=app
)

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

patents_data = load_json_data('./files/patents.json')
company_products_data = load_json_data('./files/company_products.json')

company_names = []
for company in company_products_data['companies']:
    company_names.append(company['name'])
    
def find_company(query):
    for company in company_products_data['companies']:
        if company['name'] and company['name'].lower() == query.lower():
            return company
    return None

def find_patent(patent_id):
    for patent in patents_data:
        if patent['publication_number'] and patent['publication_number'] == patent_id:
            return patent
    return None

def extract_claims_text(patent):
    claims = patent['claims'] if patent['claims'] else []
    claims = json.loads(claims)
    return "\n".join([f"Claim {claim['num']}: {claim['text']}" for claim in claims])

def select_top_two_products(products_analysis):
    likelihood_order = {"High": 3, "Moderate": 2, "Low": 1}
    sorted_products = sorted(
        products_analysis,
        key=lambda x: -likelihood_order[x['infringement_likelihood']]
    )
    return sorted_products[:2]

def assess_infringement_likelihood(relevant_claims):
    # TODO: A more precise formula might be needed
    if len(relevant_claims) >= 5:
        return "High"
    elif len(relevant_claims) >= 3:
        return "Moderate"
    else:
        return "Low"

@app.route('/analyze', methods=['POST'])
@limiter.limit("10 per hour")
def analyze():
    data = request.get_json()

    patent_id = data.get('patent_id')
    company_name = data.get('company_name')

    if not patent_id or not company_name:
        return jsonify({"error": "Both 'patent_id' and 'company_name' are required."}), 400

    patent = find_patent(patent_id)
    if not patent:
        return jsonify({"error": f"Patent ID {patent_id} not found."}), 404

    cloest_company_name = fuzzy_match(company_name, company_names)
    company = find_company(cloest_company_name)
    if not cloest_company_name:
        return jsonify({"error": f"Company '{cloest_company_name}' not found."}), 404

    patent_claims_text = extract_claims_text(patent)
    products_analysis = []
    company_products = company['products'] if company['products'] else []
    for product in company_products:
        product_desc = product['description'] if product['description'] else ''
        product_name = product['name'] if product['name'] else ''
        if not len(product_desc) or not len(product_name):
            continue
        relevant_claims, error = extract_relevant_claims(patent_claims_text, product_desc)
        if error:
            app.logger.error(error)
            continue
        explanation, error = generate_explanation(product_name, relevant_claims, product_desc)
        if error:
            app.logger.error(error)
            continue

        products_analysis.append({
            "product_name": product_name,
            "infringement_likelihood": assess_infringement_likelihood(relevant_claims),
            "relevant_claims": relevant_claims,
            "explanation": explanation,
            "specific_features": product_desc
        })
    
    top_two = select_top_two_products(products_analysis)
    overall_risk, error = generate_overall_risk_assessment(top_two)
    if error:
        app.logger.error(error)

    analysis = {
        "analysis_id": str(uuid.uuid4()),
        "patent_id": patent_id,
        "company_name": cloest_company_name,
        "analysis_date": datetime.today().strftime('%Y-%m-%d'),
        "top_infringing_products": top_two,
        "overall_risk_assessment": overall_risk
    }

    return jsonify(analysis), 200

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
    app.run(host=os.getenv("HOST"), port=int(os.getenv("PORT")), debug=is_dev)
