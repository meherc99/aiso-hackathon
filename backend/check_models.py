"""
Check available models from the OpenAI-compatible API endpoint.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_available_models():
    """Query the /v1/models endpoint to see available models."""
    
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    base_url = os.getenv(
        "OPENAI_BASE_URL",
        "https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1",
    )
    
    if not api_key:
        print("Error: No API key found in environment")
        return
    
    # Construct the models endpoint URL
    models_url = f"{base_url}/models"
    
    print(f"Querying: {models_url}")
    print(f"{'='*70}\n")
    
    try:
        response = requests.get(
            models_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        response.raise_for_status()
        
        data = response.json()
        
        if "data" in data:
            models = data["data"]
            print(f"Found {len(models)} available model(s):\n")
            
            for i, model in enumerate(models, 1):
                model_id = model.get("id", "Unknown")
                owner = model.get("owned_by", "Unknown")
                created = model.get("created", "Unknown")
                
                print(f"{i}. Model ID: {model_id}")
                print(f"   Owner: {owner}")
                print(f"   Created: {created}")
                print()
        else:
            print("Response structure:")
            print(data)
            
    except requests.exceptions.RequestException as e:
        print(f"Error querying models endpoint: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")


if __name__ == "__main__":
    check_available_models()