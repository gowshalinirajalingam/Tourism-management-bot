
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

from geminiai_bot_sql import flow_bot, analyze_intent, generate_question_to_IR, retrieve_information, save_chat, send_quotation
from SQL_IUD import get_user_records, get_chat_records, update_record

from flask import Flask, jsonify, request, Response
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import json
import time


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


inputs_dict = {
	"Name": "",
	"Email": "",
	"Address": "",
    "num_of_days": "",
    "num_of_adults": "",
    "month": "",
	"start_date": "",
	"end_date": "",
    "interests": ""
}

def personal_details_not_empty(d):
    for key, value in d.items():
        if not value:  # This checks for falsy values (None, '', 0, etc.)
            return False
    return True

@app.route('/webhook',methods=['GET',"POST"])
def whatsapp_bot():
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
		#print(body)

		if "messages" in body["entry"][0]["changes"][0]['value']:
			received_phone_num = body["entry"][0]["changes"][0]['value']["messages"][0]["from"]
			print("Receipient Phone Number:",received_phone_num)

			if received_phone_num in PHONE_NUMBER:
				user_input = body["entry"][0]["changes"][0]['value']["messages"][0]["text"]["body"]
				print("user input:",user_input)
							

				cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Service"
				user_records = get_user_records(received_phone_num, cols )

				# new user comes.
				if not user_records: #array empty

					# create record
					connection = sqlite3.connect('Digital_Tourism.db')
					cursor = connection.cursor()
					insert_record_query = '''
					INSERT INTO user_inputs (Phone_num, Name, Email, Address, Num_of_days, Num_of_adults, Month, Start_date, End_date, Interests, Service, q_to_ask )
					VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
					'''
					user_data = (received_phone_num, "", "", "", "", "", "", "", "", "", "", 1)
					cursor.execute(insert_record_query, user_data)
					connection.commit()
					connection.close()


					
				# else:
				# 	# existing user comes 
				# 	# All personal important details are filled.
				# 	# if personal_details_not_empty(user_records[0]):

				# 	# 	classes = ["Confirm_booking", "Other"]
				# 	# 	intent = analyze_intent(user_input, classes)
				# 	# 	print("intent:", intent)

				# 	# 	if "Confirm_booking" in intent:
				# 	# 		cols = "Service"
				# 	# 		user_records = get_user_records(received_phone_num, cols)

				# 	# 		if user_records:
				# 	# 			if user_records[0]["Service"] == "Driver":
				# 	# 				response = "Please book the driver via https://srilankadriverguide.com/ and the quotation will be sent to your email. \nDo you have any questions to ask?"
				# 	# 			else:
				# 	# 				response = "Hotel detail and quotation will be sent to your email. \nDo you have any questions to ask?"
				# 	# 		else:
				# 	# 			# Sometimes if the service details are not asked by the bot this question will be raised.
				# 	# 			response = "Would you like to have driver services only, or both driver and hotel bookings?"
							
				# 	# 		#saving the chat to chat_history (inside message_store in db)
				# 	# 		save_chat(user_input, response, received_phone_num)
						
				# 	# 	else:  
				# 			#  Call flow_bot()
				# 			response = flow_bot(user_input, received_phone_num)

				# 	# Some values are missing from Name, Email, Num_of_days, Num_of_adults .
				# 	# else:
				# 	# 	classes = ["Question", "Other"]
				# 	# 	intent = analyze_intent(user_input, classes)
				# 	# 	print("intent:", intent)

				# 	# 	if "Question" in intent:
				# 	# 		#  Call flow_bot()
				# 	# 		response = flow_bot(user_input, received_phone_num)
				# 	# 	else:
				# 	# 		# gather information
				# 	# 		response = generate_question_to_IR(user_input, received_phone_num, user_records)
				
				classes = ["Question", "Other"]
				intent = analyze_intent(user_input, classes)
				print("intent:", intent)
			
				if "Other" in intent:
					#Retrieve information and update DB user_inputs table
					retrieve_information(user_input,received_phone_num )
# 					columns = "q_to_ask"
# 					record_json = get_user_records(received_phone_num, columns)
# 					id = record_json[0][columns]   #assumed user will have only one record. In future user may have multiple for each trips.
# 					response = track_flow(id)

# 					next_q_id = id + 1
# 					query = f"""
# UPDATE user_inputs
# SET q_to_ask = {next_q_id}
# WHERE Phone_num = {received_phone_num};
# 					"""

# 					update_record(query)
					# keys = user_records[0]
					# track_flow(keys)
					# save_chat(user_input, response, received_phone_num)
					response = flow_bot(user_input, received_phone_num)


				elif "Question" in intent:
					response = flow_bot(user_input, received_phone_num)

				
				
				

				if not response:  # This checks for empty strings, None, or other falsy values
					response = flow_bot(user_input, received_phone_num)
				


				
				
				print("response:",response)

				#Send Itinerary plan pdf
				if "itineraryAPI" in response:
					output = send_itinerary_pdf_to_whatsapp(received_phone_num)
					# save_chat(user_input, output, received_phone_num)

					return Response(body, 200)
				
				elif "quotationAPI" in response:
					response, pdf_path_hotel = send_quotation(received_phone_num)

					if pdf_path_hotel is not None: #Hotel list pdf is generated
						output = send_hotel_list_and_price_pdf_to_whatsapp(received_phone_num, pdf_path_hotel)

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

	

				return Response(body, 200)
			else:
				print("This phone number is not allowed to chat.")
				return Response(body, 200)


		elif "statuses" in body["entry"][0]["changes"][0]['value']:
			read_status = body["entry"][0]["changes"][0]['value']["statuses"][0]["status"]
			print("Message read status:",read_status)
			return Response(body, 200)
		else:
			return Response(body, 200)





def send_itinerary_pdf_to_whatsapp(received_phone_num):
	media_id = 892302872719363
	output = "Based on your interests here's the suggested itinerary for your trip. Does this look good to you?"

	#send file from whatsapp media
	url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
	media_id = '1019176409797168'
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
	output = f"These are the hotel list with price details and saved in {pdf_path_hotel}."

	#send file from whatsapp media
	url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
	media_id = '1678828762869228'
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

if __name__ == '__main__':
	ssl_context_f=('/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/fullchain.pem', '/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/privkey.pem')
	app.run(ssl_context=ssl_context_f, host='0.0.0.0',port=os.environ.get("PORT", 5000))


