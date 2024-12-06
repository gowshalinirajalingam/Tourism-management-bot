
"""
Test Code
"""
# from geminiai_bot import flow_bot
# user_question = "What is the capital of France?"
# response = flow_bot(user_question)
# print("Bot:", response)


"""
Main Code
"""

from geminiai_bot_sql import flow_bot, analyze_intent, generate_question_to_IR, retrieve_information, save_chat, send_quotation, validate_inputs, answer_common_questions
from SQL_IUD import get_user_records, get_chat_records, update_record, get_media_id

from flask import Flask, jsonify, request, Response
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import json
import time
import traceback


__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import sqlite3

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.environ["GOOGLE_API_KEY"]
WHAT_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER = os.getenv("RECIPIENT_WAID")
VERSION = os.getenv("VERSION")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

print("GEMINI_API_KEY", GEMINI_API_KEY)




@app.route('/webhook',methods=['GET',"POST"])
def whatsapp_bot():
	if request.method == 'GET':
		try:
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
		except Exception as e:
			print(f"Exception inside GET request at {get_current_date_time()} : {e}")
			tb = traceback.format_exc()
			print(tb)
			response = "Error occured. Please contact support."
			send_message(response, received_phone_num)
			return Response(body, 200)
			

	if request.method == 'POST':

		try:
			body = request.get_json()



			if "messages" in body["entry"][0]["changes"][0]['value']:
				
				print(body)

				received_phone_num = body["entry"][0]["changes"][0]['value']["messages"][0]["from"]
				timestamp = body["entry"][0]["changes"][0]['value']["messages"][0]["timestamp"]
				print("Receipient Phone Number:",received_phone_num)

				if received_phone_num in PHONE_NUMBER:

					#Validate input type
					input_type = body["entry"][0]["changes"][0]['value']["messages"][0]["type"]
					if  input_type != 'text':
						response = f"The {input_type} is not supported at the moment"
						send_message(response, received_phone_num)
						return Response(body, 200)

					#If the input type is text proceed
					user_input = body["entry"][0]["changes"][0]['value']["messages"][0]["text"]["body"]
					print("user input:",user_input)
								
					cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Num_of_kids, Service, Last_message_retrieve_time"
					user_records = get_user_records(received_phone_num, cols )

					# new user comes.
					if not user_records: #array empty

						# create record
						connection = sqlite3.connect('Digital_Tourism.db')
						cursor = connection.cursor()
						insert_record_query = '''
INSERT INTO user_inputs (Phone_num, Name, Email, Address, Num_of_days, Num_of_adults, Num_of_kids, Month, Start_date, End_date, Interests, Service, Last_message_retrieve_time )
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
						'''
						user_data = (received_phone_num, "", "", "", "", "", "", "", "", "", "", "", timestamp)
						cursor.execute(insert_record_query, user_data)
						connection.commit()
						connection.close()
					
					print(user_records)

					#Discard recieving old messages
					cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Num_of_kids, Service, Last_message_retrieve_time"
					user_records_updated = get_user_records(received_phone_num, cols )  #for the first time the user_records will be empty. so have to retrieve again after insertion.
					Last_message_retrieve_time = user_records_updated[0]["Last_message_retrieve_time"]
					if discard_old_messages(timestamp, Last_message_retrieve_time):
						print("Recieved old message. Discarded")
						return Response(body, 200)
					else:
						query = f"""
UPDATE user_inputs
SET Last_message_retrieve_time = {timestamp}
WHERE Phone_num = {received_phone_num};
						"""
						update_record(query)

					
					classes = ["Question", "Other"]
					intent = analyze_intent(user_input, classes)
					print("intent:", intent)
				
					if "Other" in intent:
						#Retrieve information and update DB user_inputs table
						retrieve_information(user_input,received_phone_num )

						#Validate inputs
						cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Num_of_kids, Service, Last_message_retrieve_time"
						user_records_updated = get_user_records(received_phone_num, cols )  # retrieve records after updating the extracted values
						status, msg = validate_inputs(user_records_updated[0], received_phone_num)

						if not status:
							response = msg
							send_message(response, received_phone_num)
							return Response(body, 200)

						#Call flow bot()
						response = flow_bot(user_input, received_phone_num)

					elif "Question" in intent:
						#call flow bot
						response = answer_common_questions(user_input, received_phone_num)

						#If the user asks about trip planning call the flow bot
						if "travel_plan_API" in response:
							response = flow_bot(user_input, received_phone_num)

					if not response:  # This checks for empty strings, None, or other falsy values
						response = flow_bot(user_input, received_phone_num)
					

					print("response:",response)
					print("response:",type(response))


					#Send Itinerary plan pdf
					if "itineraryAPI" in response:
						days = user_records[0]["Num_of_days"]
						month = user_records[0]["Month"]

						output = send_itinerary_pdf_to_whatsapp(received_phone_num, days, month)
						# save_chat(user_input, output, received_phone_num)

						return Response(body, 200)
					
					#Send Quotation details and pdf
					elif "quotationAPI" in response:
						response, pdf_path_hotel = send_quotation(received_phone_num)

						if pdf_path_hotel is not None: #Hotel list pdf is generated
							output = send_hotel_list_and_price_pdf_to_whatsapp(received_phone_num, pdf_path_hotel)
					

					send_message(response, received_phone_num)
					return Response(body, 200)
				else:
					print("This phone number is not allowed to chat.")
					return Response(body, 200)

			#Send message status whether sent or delivered.
			elif "statuses" in body["entry"][0]["changes"][0]['value']:
				read_status = body["entry"][0]["changes"][0]['value']["statuses"][0]["status"]
				print("Message read status:",read_status)
				return Response(body, 200)
			else:
				return Response(body, 200)
		except Exception as e:
			# print(f"Exception type: {type(e).__name__}")
			# print(f"Exception message: {e}")
			tb = traceback.format_exc()
			print(tb)
			
			print(f"Exception inside POST request at {get_current_date_time()} : {e}")
			response = "Error occured. Please contact support."
			send_message(response, received_phone_num)
			return Response(body, 200)







def send_itinerary_pdf_to_whatsapp(received_phone_num, days, month):
	records = get_media_id(days, month)
	media_id = records[0]["media_id"]
	print("media_id",media_id)
	output = "Based on your interests here's the suggested itinerary for your trip. Does this look good to you?"

	#send file from whatsapp media
	url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
	headers = {
		f"Authorization": f"Bearer {WHAT_TOKEN}",
		"Content-Type": "application/json"
	}
	data = {
		"messaging_product": "whatsapp",
		"to": received_phone_num,
		"type": "document",

		"document": {          
				"id": media_id,
				"caption": output, 
				"filename": "itinerary.pdf"
				}
	}

	response = requests.post(url, json=data, headers=headers)  #send msg to whatsapp
	print("itinerary pdf status:",response.text)
	return output

def send_hotel_list_and_price_pdf_to_whatsapp(received_phone_num, pdf_path_hotel):
	output = f"These are the hotel list with price details."

	media_id = upload_hotel_list(pdf_path_hotel)

	#send file from whatsapp media
	url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
	headers = {
		f"Authorization": f"Bearer {WHAT_TOKEN}",
		"Content-Type": "application/json"
	}
	data = {
		"messaging_product": "whatsapp",
		"to": received_phone_num,
		"type": "document",

		"document": {          
				"id": media_id,
				"caption": output, 
				"filename": "hotel_list.pdf"
				}
	}

	response = requests.post(url, json=data, headers=headers)  #send msg to whatsapp
	print("hotel list pdf status:",response.text)
	return output

def upload_hotel_list(pdf_path_hotel):

	url = 'https://graph.facebook.com/v20.0/'+PHONE_NUMBER_ID+'/media'
	headers = {
		'Authorization': f'Bearer {WHAT_TOKEN}',
	}
	f = open(pdf_path_hotel, "rb")
	files = {
		'file':(os.path.basename(f.name), f, 'application/pdf'),
		'type': (None, "pdf"),
		'messaging_product': (None, "whatsapp"),
	}

	response = requests.post(url, headers=headers, files=files)
	r = response.text
	media_id = json.loads(r)["id"]

	return media_id

def get_current_date_time():
	from datetime import datetime

	# Get the current date and time
	now = datetime.now()
	formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

	formatted_now
	return formatted_now

def send_message(response, received_phone_num):
	url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
	headers = {
		f"Authorization": f"Bearer {WHAT_TOKEN}",
		"Content-Type": "application/json"
	}
	data = {
		"messaging_product": "whatsapp",
		"to": received_phone_num,
		"type": "text",
		"text": {"body": response}
	}

	response = requests.post(url, json=data, headers=headers)  #send msg to whatsapp

def discard_old_messages(timestamp, Last_message_retrieve_time):
	#take timestamp of latest message request
	b = Last_message_retrieve_time  > timestamp   #this is a old message. return true. For new message false
	return b


if __name__ == '__main__':
	# ssl_context_f=('/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/fullchain.pem', '/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/privkey.pem')
	# app.run(ssl_context=ssl_context_f, host='0.0.0.0',port=os.environ.get("PORT", 5000))
	app.run(host='0.0.0.0',port=os.environ.get("PORT", 5000))


