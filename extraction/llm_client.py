"""
Minimal Groq connectivity test.
Purpose: confirm our .env key loads correctly and the Groq client works,
before we build any real extraction logic on top of it.
"""

import os
from dotenv import load_dotenv
from groq import Groq

# Loads variables from your .env file into the environment
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


def test_connection():
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "user", "content": "Say hello in exactly 3 words."}
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(test_connection())