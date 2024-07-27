from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from langchain_community.chat_models import ChatOllama
from langchain_aws import ChatBedrock

import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import json
import time
import base64
import boto3
import os

import pymysql


from dotenv import load_dotenv
load_dotenv()
#--------------- Credentials Configuration ---------------#
region_name_1 = os.environ['REGION_NAME_1']
region_name_2 = os.environ['REGION_NAME_2']
aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
#---------------------------------------------------------#

model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

### LLM Accession ###
bedrock_runtime = boto3.client("bedrock-runtime",
    region_name=region_name_1,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

### RDS Connection ###
host = os.environ['RDS_HOST']
user = os.environ['RDS_USER']
password = os.environ['RDS_PASSWORD']
port = int(os.environ['RDS_PORT'])


class State(TypedDict):
    device: str
    filepath: str
    image64: str
    type: int
    contacts: list
    firestage: int


def encode_image(state):
    filepath = state['filepath']

    with open(filepath, "rb") as f:
        image_data = f.read()
        encoded_string = base64.b64encode(image_data).decode("utf-8")

        print("Image -> base64")

        return { "image64": encoded_string }


def state_determine(state):
    device = state["device"]

    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="pyrosense"
    )
    cursor = connection.cursor()
    cursor.execute(f"SELECT state FROM cameras WHERE device = '{device}'")

    result = str(cursor.fetchone()[0])

    print("Get Previous Firestage ->", ["Safe", "Low", "Moderate", "High", "Extreme"][int(result)])

    cursor.close()
    connection.close()

    return result

def fire_inspect(state):
    image = state['image64']

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image,
                            },
                        },
                        {"type": "text", "text": """From the image, inspect and catagorize the type of fire into class 1, 2, 3 based on the following:
1. Man-made fire: a fire that is intentionally created by humans, rather than occurring naturally. This can include fire made for purposes such as cooking, heating, or entertainment (e.g., campfires, bonfires)
2. Fake fire: an imitation of real fire, often created for decorative or safety purposes. This can include electric or LED flames, holographic projections, or other visual effects designed to mimic the appearance of actual flames without producing heat or requiring combustion.
3. Dangerous fire: a fire that poses significant risks to people, property, or the environment. This includes fires that spread rapidly, are difficult to control, or cause significant harm. Dangerous fires can result from various causes, such as wildfires, house fires, industrial accidents, or arson.
No commentation, only number"""},
                    ],
                }
            ],
        }
    )

    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=body
    )

    response_body = json.loads(response.get("body").read())

    print("Type: 1-Man-made, 2-Fake fire, 3-Dangerous fire")
    print("Inspection ->", response_body['content'][0]['text'])

    return { "type": str(response_body['content'][0]['text']) }


def get_associate_persons(state):
    device = state["device"]
    distance = 5 #km

    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="pyrosense"
    )
    cursor = connection.cursor()

    cursor.execute(f"SELECT latitude, longitude FROM cameras WHERE device = '{device}'")
    position = tuple(cursor.fetchone())
    latitude = position[0]
    longitude = position[1]
    print(position)

    cursor.execute(query=
    f"""SELECT email 
    FROM users 
    WHERE ( 6371 * acos(
        cos(radians({latitude})) * cos(radians(users.latitude)) *
        cos(radians(users.longitude) - radians({longitude})) +
        sin(radians({latitude})) * sin(radians(users.latitude))
    )) < {distance}""")
    contacts = [contact[0] for contact in cursor.fetchall()]

    print("Contacts ->", contacts)

    cursor.close()
    connection.close()

    return { "contacts": contacts }


def send_emails(state):
    port = 465
    smtp_server = "smtp.gmail.com"
    sender_email = os.environ["EMAIL_NAME"]
    receiver_emails = state["contacts"]
    password = os.environ["EMAIL_PASSWORD"]

    subject = "⚠️🔥 Fire Detected in Your Area 🔥⚠️"
    body = "Our system has detected that there's fire occuring in your area. Please inspect the area or contact the fire officer"
    attachment_path = state['filepath']
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(receiver_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with open(attachment_path, 'rb') as attachment:

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(attachment_path)}')

        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_emails, text)

        print("Send Email -> Success")

def fire_stage_estimation(state):
    image = state['image64']

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image,
                            },
                        },
                        {"type": "text", "text": """From the image, give the severity of fire level in range 1-4. based on the following:
1. Low: Small, controllable, low spread risk.
2. Moderate: Expanding, moderate spread risk.
3. High: Rapidly spreading, high spread risk.
4. Extreme: Uncontrollable, extreme spread risk.
No commentation, only number"""},
                    ],
                }
            ],
        }
    )

    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=body
    )

    response_body = json.loads(response.get("body").read())

    print("Scale: 1-Low, 2-Moderate, 3-High, 4-Extreme")
    print("Firestage Estimation Scale ->", response_body['content'][0]['text'])

    return { "firestage": response_body['content'][0]['text'] }


def pin_map(state):
    device = state["device"]
    firestage = state['firestage']

    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="pyrosense"
    )
    cursor = connection.cursor()
    print(device)
    cursor.execute(f"UPDATE pyrosense.cameras SET pyrosense.cameras.state = {firestage}, pyrosense.cameras.updated = CURRENT_TIMESTAMP WHERE device = '{device}'")
    print("Update Area -> Success")

    cursor.close()
    connection.commit()
    connection.close()


def pass_through(state):
    pass


workflow = StateGraph(State)
workflow.add_node("encoding", encode_image)
workflow.add_node("inspection", fire_inspect)
workflow.add_node("pass", pass_through)
workflow.add_node("association", get_associate_persons)
workflow.add_node("notification", send_emails)
workflow.add_node("estimation", fire_stage_estimation)
workflow.add_node("update", pin_map)


workflow.set_entry_point("encoding")
workflow.add_conditional_edges("encoding",
    state_determine,
    {
        "0": "pass",
        "1": END,
        "2": END,
        "3": END,
        "4": END,
    }
)
workflow.add_edge("pass", "inspection")
workflow.add_conditional_edges("inspection", 
    lambda state: state['type'],
    {
        "1": END,
        "2": END,
        "3": "association",
    },
)
workflow.add_conditional_edges("association", 
    lambda state: "available" if state['contacts'] else "unavailable",
    {
        "unavailable": "estimation",
        "available": "notification"
    }
)
workflow.add_edge("notification", "estimation")
workflow.add_edge("estimation", "update")

app = workflow.compile()


if __name__ == "__main__":
    #x = app.invoke({"filepath": "./test.jpeg"})
    #print(x["image64"])
    #test123()
    #send_emails({ "filepath": "./test.jpeg", "contacts": ["65011146@kmitl.ac.th", "65010811@kmitl.ac.th"] })
    #get_associate_persons(0)
    #print(f"hey {1}")
    #fire_stage_estimation(encode_image({"filepath": "./test5.jpg"}))
    #fire_inspect(encode_image({"filepath": "./20240726_031337.jpeg"}))
    #state_determine({ "device": 'dfa49df0-600a-480e-aedf-9cc140857424' })
    #get_associate_persons({ "device": 'dfa49df0-600a-480e-aedf-9cc140857424' })
    pin_map({ "device": 'dfa49df0-600a-480e-aedf-9cc140857424', "firestage": "0" })
    pass