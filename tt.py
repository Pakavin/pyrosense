import os
from pathlib import Path
import base64
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
import boto3
import json

def Is_it_real_fire(image_path):
    # Set your own keys
    os.environ["AWS_ACCESS_KEY_ID"] = ""
    os.environ["AWS_SECRET_ACCESS_KEY"] = ""
    os.environ["AWS_DEFAULT_REGION"] = 'us-east-1'

    MODEL_ID = "anthropic.claude-v2:1"
    MODEL_KWARGS = {
        "max_tokens": 2048,
        "temperature": 0.1,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman"],
    }

    bedrock_runtime = boto3.client("bedrock-runtime")

    model = ChatBedrock(
        client=bedrock_runtime,
        model_id=MODEL_ID,
        model_kwargs=MODEL_KWARGS,
    )

    messages = [
        ("system", "You are an honest and helpful bot. You reply to the question in a concise and direct way."),
        ("human", "Analyze the image of a fire and determine if it is a significant hazard or a benign source (e.g., cooking flame). Output the result as JSON with: { \"status\": 0 or 1 } Where: 0 = Safe fire (e.g., cooking flame) 1 = Hazardous fire. The base64 image is: {image_base64}"),
    ]

    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | model | StrOutputParser()

    def analyze_fire_image(image_path):
        # Load and convert image to base64
        image_file = Path(image_path)
        image_base64 = base64.b64encode(image_file.read_bytes()).decode('utf-8')

        question = {"image_base64": image_base64}
        response = chain.invoke(question)

        try:
            json_response = json.loads(response)
            return json_response["status"]
        except (json.JSONDecodeError, KeyError):
            # Handle error cases, e.g., return -1 for invalid response
            return -1

    # Example usage
    response = analyze_fire_image(image_path)
    return response

# Example usage
response = Is_it_real_fire("path_to_your_image.jepg")
print(response)