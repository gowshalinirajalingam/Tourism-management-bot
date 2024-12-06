from flask import Flask, jsonify, request, Response
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.environ["GOOGLE_API_KEY"]
WHAT_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER = os.getenv("RECIPIENT_WAID")
VERSION = os.getenv("VERSION")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")



print("GEMINI_API_KEY", GEMINI_API_KEY)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
def ai_response(ask):
    response = model.generate_content(
        ask,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7)
    )
    return response.text

@app.route('/webhook',methods=['GET',"POST"])
def hello_world():
	if request.method == 'GET':
		mode = request.args.get('hub.mode')
		print("Mode", mode)
		verify_token = request.args.get('hub.verify_token')
		print("verify_token", verify_token)

		challenge = request.args.get('hub.challenge')

		if mode and verify_token:
			if mode == 'subscribe' and verify_token == VERIFY_TOKEN:
				return Response(challenge,200)
			else:
				return Response("",403)
		else:
			return

	if request.method == 'POST':
		body = request.get_json()
		print(body)

		if "messages" in body["entry"][0]["changes"][0]['value']:
			if body["entry"][0]["changes"][0]['value']["messages"][0]["from"] == PHONE_NUMBER:
				user_question = body["entry"][0]["changes"][0]['value']["messages"][0]["text"]["body"]
				print("user_question",user_question)
				response = ai_response(user_question)
				print("response",response)
				url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
				headers = {
					f"Authorization": f"Bearer {WHAT_TOKEN}",
					"Content-Type": "application/json"
				}
				data = {
					"messaging_product": "whatsapp",
					"to": PHONE_NUMBER,
					"type": "text",
					"text": {"body": response}
				}

				response = requests.post(url, json=data, headers=headers)  #send msg to whatsapp
				print(response.text)
				return Response(body, 200)
		elif "statuses" in body["entry"][0]["changes"][0]['value']:
			read_status = body["entry"][0]["changes"][0]['value']["statuses"][0]["status"]
			print("Message read status:",read_status)
			return Response(body, 200)
		else:
			return Response(body, 200)





if __name__ == '__main__':
	app.run(host='0.0.0.0',port=os.environ.get("PORT", 5000))

