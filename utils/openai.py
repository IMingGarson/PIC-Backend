import openai
import json
import os
from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

openai.api_key = os.getenv("OPENAI_API_KEY")

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
        return relevant_claims, ''
    except Exception as e:
        return [], f"Error extracting relevant claims: {e}"

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
        return response.choices[0].message.content.strip(), ""
    except Exception as e:
        return "", f"Error generating explanation: {e}"

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
        return response.choices[0].message.content.strip(), ""
    except Exception as e:
        return "", f"Error generating overall risk assessment: {e}"