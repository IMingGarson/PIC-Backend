import json
import openai
import os
import uuid
from flask_cors import CORS
from datetime import datetime
from flask import Flask, request, jsonify
from os.path import join, dirname
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
openai.api_key = os.getenv("OPENAI_API_KEY")

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

def find_patent(patent_id):
    for patent in patents_data:
        if patent['publication_number'] and patent['publication_number'] == patent_id:
            return patent
    return None

def find_company(company_name):
    companies = company_products_data['companies'] if company_products_data['companies'] else []
    for company in companies:
        if company['name'] and company['name'].lower() == company_name.lower():
            return company
    return None

def extract_claims_text(patent):
    claims = patent['claims'] if patent['claims'] else []
    claims = json.loads(claims)
    return "\n".join([f"Claim {claim['num']}: {claim['text']}" for claim in claims])

def extract_relevant_claims(patent_claims, product_description):
    prompt = f"""
    Given the following patent claims:
    {patent_claims}
    
    And the product description:
    {product_description}
    
    Identify which claims are potentially infringed by this product and list them as comma-separated numbers.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that helps analyze patent claims against product descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        claims_text = response.choices[0].message.content.strip()
        relevant_claims = [claim.strip() for claim in claims_text.split(",") if claim.strip().isdigit()]
        return relevant_claims
    except Exception as e:
        app.logger.error(f"Error extracting relevant claims: {e}")
        return []

def assess_infringement_likelihood(relevant_claims):
    # TODO: A more precise formula might be needed
    if len(relevant_claims) >= 5:
        return "High"
    elif len(relevant_claims) >= 3:
        return "Moderate"
    else:
        return "Low"

def generate_explanation(product_name, relevant_claims, product_description):
    prompt = f"""
    Generate a detailed explanation for why the product "{product_name}" potentially infringes the following patent claims: {relevant_claims}, specifically detailing which claims are at issue. 
    Include references to the specific features: {product_description}.
    Omit any unncessary step-by-step analysis, clarification and redundant words, and provide a summary no more than 100 English words.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that helps analyze patent claims against product descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"Error generating explanation: {e}")
        return "Explanation unavailable due to an error."

def generate_overall_risk_assessment(products_analysis):
    prompt = f"""
    Based on the following infringement likelihoods and relevant claims of the top infringing products, provide an overall risk assessment.
    Omit any unncessary step-by-step analysis, clarification and redundant words, and provide a summary no more than 70 English words.
    {json.dumps(products_analysis, indent=2)}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that helps analyze patent claims against product descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"Error generating overall risk assessment: {e}")
        return "Overall risk assessment unavailable due to an error."

def select_top_two_products(products_analysis):
    likelihood_order = {"High": 3, "Moderate": 2, "Low": 1}
    sorted_products = sorted(
        products_analysis,
        key=lambda x: -likelihood_order[x['infringement_likelihood']]
    )
    return sorted_products[:2]

@app.route("/slow")
@limiter.limit("5 per minute")
def slow():
    return "5 per minute!"

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

    company = find_company(company_name)
    if not company:
        return jsonify({"error": f"Company '{company_name}' not found."}), 404

    patent_claims_text = extract_claims_text(patent)
    products_analysis = []
    for product in company.get('products', []):
        product_desc = product['description'] if product['description'] else ''
        product_name = product['name'] if product['name'] else ''
        relevant_claims = extract_relevant_claims(patent_claims_text, product_desc)
        infringement_likelihood = assess_infringement_likelihood(relevant_claims)
        explanation = generate_explanation(product_name, relevant_claims, product_desc)
        products_analysis.append({
            "product_name": product_name,
            "infringement_likelihood": infringement_likelihood,
            "relevant_claims": relevant_claims,
            "explanation": explanation,
            "specific_features": product_desc
        })
        

    top_two = select_top_two_products(products_analysis)
    overall_risk = generate_overall_risk_assessment(top_two)

    analysis = {
        "analysis_id": str(uuid.uuid4()),
        "patent_id": patent_id,
        "company_name": company.get('name', ''),
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
    app.run(host='0.0.0.0', port=5000, debug=True)
