#!/usr/bin/env python3
"""
Test script to verify the custom OpenAI endpoint is working correctly.
"""

import os
from dotenv import load_dotenv
from product_search import get_openai_client  # Adjust imports based on actual functions

# Load environment variables from .env file
load_dotenv()

if __name__ == "__main__":
    client = get_openai_client()
    
    response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "user", "content": "hello world"}
            ],
            # response_format={"type": "json_object"},
            temperature=1
        )
    print(response.choices[0].message.content)