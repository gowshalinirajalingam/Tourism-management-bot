
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

from geminiai_bot_sql import flow_bot, analyze_intent, retrieve_information, send_quotation, validate_inputs, llm_common
from SQL_IUD import get_user_records, update_record, get_media_id, get_chat_records, delete_record, delete_record, get_records
from tools import save_chat

from flask import Flask, request, Response
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import json
import traceback
import ast
from datetime import datetime


# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import sqlite3

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.environ["GOOGLE_API_KEY"]
WHAT_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER = os.getenv("RECIPIENT_WAID")
VERSION = os.getenv("VERSION")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
AGENT = os.getenv("AGENT")

#string to array
AGENT = ast.literal_eval(AGENT)
PHONE_NUMBER = ast.literal_eval(PHONE_NUMBER)

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
			response = "Error occured."
			send_message(response, received_phone_num)
			return Response(body, 200)
			

	if request.method == 'POST':

		try:
			body = request.get_json()



			if "messages" in body["entry"][0]["changes"][0]['value']:
				
				print(body)

				received_phone_num = body["entry"][0]["changes"][0]['value']["messages"][0]["from"]
				timestamp = body["entry"][0]["changes"][0]['value']["messages"][0]["timestamp"]  #this is unix timestamp
				normal_timestamp = datetime.fromtimestamp(int(timestamp))				#this is normal time stamp
				response = ''

				print("Receipient Phone Number:",received_phone_num)

				if received_phone_num in PHONE_NUMBER or received_phone_num in AGENT:

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
INSERT INTO user_inputs (Phone_num, Name, Email, Address, Num_of_days, Num_of_adults, Num_of_kids, Month, Start_date, End_date, Interests, Service, Last_message_retrieve_time, Agent_mode, Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number )
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
						'''
						user_data = (received_phone_num, "", "", "", "", "", "", "", "", "", "", "", normal_timestamp, "off","", "", "", "", "", "")
						cursor.execute(insert_record_query, user_data)
						connection.commit()
						connection.close()
					print("user_records",user_records)

# 					#create agent records
# 					query = f"SELECT Agent_pno from agent where Agent_pno = '{AGENT[0]}' "
# 					agent_records = get_records(query)

# 					if not agent_records: #array empty

# 						# create record
# 						connection = sqlite3.connect('Digital_Tourism.db')
# 						cursor = connection.cursor()
# 						insert_record_query = '''
# INSERT INTO agent (Agent_pno, Client_pno )
# VALUES (?, ?);
# 						'''
# 						user_data = (AGENT[0], "")
# 						cursor.execute(insert_record_query, user_data)
# 						connection.commit()
# 						connection.close()
# 					print("agent_records",agent_records)

					#Discard recieving old messages
					cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Num_of_kids, Service, Last_message_retrieve_time, Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number"
					user_records_updated = get_user_records(received_phone_num, cols )  #for the first time the user_records will be empty. so have to retrieve again after insertion.
					Last_message_retrieve_time = user_records_updated[0]["Last_message_retrieve_time"]
					
					date_format = "%Y-%m-%d %H:%M:%S"
					Last_message_retrieve_time = datetime.strptime(Last_message_retrieve_time, date_format)
					if discard_old_messages(normal_timestamp, Last_message_retrieve_time):
						print("Recieved old message. Discarded")
						return Response(body, 200)
					else:
						query = f"""
UPDATE user_inputs
SET Last_message_retrieve_time = '{normal_timestamp}'
WHERE Phone_num = {received_phone_num};
						"""
						update_record(query)
					

					# clear chat history
					if user_input.lower() == "clear":
						query = f"DELETE FROM message_store WHERE session_id ={received_phone_num};"
						delete_record(query)
						print(query)
						query = f"UPDATE user_inputs SET Name = '', Email = '', Address = '', Num_of_days = '', Num_of_adults = '', Num_of_kids = '', Month = '', Start_date = '', End_date = '', Interests = '', Service = '', Arrival_date = '', Arrival_time = '', Arrival_flight_number = '' , Depature_date = '', Depature_time = '', Depature_flight_number = '' WHERE Phone_num = {received_phone_num};"
						delete_record(query)
						print(query)
						response = "The database is cleared. How can I help you?"
						save_chat(user_input, response, received_phone_num)
						send_message(response, received_phone_num)
						return Response(body, 200)
					
					

					#Stop/ Start chat after connecting with agent
						#Get agent mode from the data base

					if received_phone_num in AGENT:

						#Get client pno
						# query = f"SELECT Client_pno from agent WHERE Agent_pno = '{AGENT[0]}'"
						# records = get_records(query)
						# print("agent records", records)
						# client_phone_num = records[0]["Client_pno"]
						# print("client pno:", client_phone_num)
						client_phone_num = user_input.split(",")[-1].strip()
						print("client_phone_num:",client_phone_num)

						try:
							if client_phone_num:
								cols = "Agent_mode"
								user_records_updated = get_user_records(client_phone_num, cols )  #for the first time the user_records will be empty. so have to retrieve again after insertion.
								Agent_mode = user_records_updated[0]["Agent_mode"]

								agent_handling(user_input, received_phone_num, Agent_mode, client_phone_num)
								return Response(body, 200)
							else: 
								response = "Add customer number in the input."
								send_message(response, AGENT[0])
								return Response(body, 200)
						except:
							response = "Send the response in the format: <message>,<customer phone number>"
							send_message(response, AGENT[0])
							return Response(body, 200)

					else:
						cols = "Agent_mode"
						user_records_updated = get_user_records(received_phone_num, cols )  #for the first time the user_records will be empty. so have to retrieve again after insertion.
						Agent_mode = user_records_updated[0]["Agent_mode"]

						if Agent_mode == "on":
							client_phone_num = received_phone_num
							agent_handling(user_input, received_phone_num, Agent_mode, client_phone_num)
							return Response(body, 200)


					classes = ["Question", "Other"]
					intent = analyze_intent(user_input, classes)
					print("intent:", intent)
				
					if "Other" in intent:
						#Retrieve information and update DB user_inputs table
						intent_of_prev_question = retrieve_information(user_input, received_phone_num)

						if "greet" in intent_of_prev_question.lower():
							prompt = """

Extract user_input from inputs.

Evaluate the following user input to determine if it specifically means planning for a trip or greetings.
If the input does not explicitly indicate trip planning or greetings, respond with "invalid."

User Input: user_input

"""							
							keys = {
								"user_input" : user_input,
								"received_phone_num": received_phone_num
							}

							response = llm_common(prompt, False, keys)

							print("greeting",intent_of_prev_question,response)
							if 'invalid' in response:
								response = "The initial message should have a meaning of planning for a trip."
								send_message(response, received_phone_num)
								agent_handover(user_input, received_phone_num)
								return Response(body, 200)
								# send_message(response, received_phone_num)
								# save_chat(user_input, response, received_phone_num)
								# return Response(body, 200)
							

						# #Validate inputs
						cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Num_of_kids, Service, Last_message_retrieve_time, Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number"
						user_records_updated = get_user_records(received_phone_num, cols )  # retrieve records after updating the extracted values
						status, msg = validate_inputs(intent_of_prev_question, user_input, user_records_updated, received_phone_num)

						if not status:
							response = msg
							if "Our consultant will contact you to assist" in response:
								agent_handover(user_input, received_phone_num)
								return Response(body, 200)
							
							send_message(response, received_phone_num)
							save_chat(user_input, response, received_phone_num)
							return Response(body, 200)
						
						if intent_of_prev_question in ["Flight details","Flight_details"] and status == True:  #added bcz if we direct to flow bot it will retun blank.
							response = "Great! We received the flight details. What is your full name as per yout passport?"
							send_message(response, received_phone_num)
							save_chat(user_input, response, received_phone_num)
							return Response(body, 200)

						#Call flow bot()
						response = flow_bot(user_input, received_phone_num, user_records_updated, intent)

					elif "Question" in intent:
						# #call flow bot
						# response = answer_common_questions(user_input, received_phone_num)

						# #If the user asks about trip planning call the flow bot
						# if "travel_plan_API" in response:
						# 	response = flow_bot(user_input, received_phone_num)
						response = flow_bot(user_input, received_phone_num, user_records_updated, intent)


					if not response.strip():  # This checks for empty strings, None, or other falsy values
						print("Error: The response is blank or contains only whitespace.")
						response = "The answer you provided is unclear. Can you provide in another way?"
						# save_chat(user_input, response, received_phone_num)

					
					

					print("response:",response)
					print("response:",type(response))


					#Send Itinerary plan pdf
					if "itineraryAPI" in response:
						days = user_records[0]["Num_of_days"]
						month = user_records[0]["Month"]

						output = send_itinerary_pdf_to_whatsapp(received_phone_num, days, month)
						save_chat(user_input, output, received_phone_num)

						return Response(body, 200)
					
					#Send Quotation details and pdf
					elif "quotationAPI" in response:
						response, pdf_path_hotel = send_quotation(received_phone_num)

						if pdf_path_hotel is not None: #Hotel list pdf is generated
							output = send_hotel_list_and_price_pdf_to_whatsapp(received_phone_num, pdf_path_hotel)
							save_chat(user_input, output, received_phone_num)

					
					elif "flightAPI" in response:
						response = """
Great! to prepare your invoice, I need some flight details. Could you please tell me your 
	- Arrival Date:
	- Arrival Flight number:
	- Arrival Time:
	- Depature Date:
	- Depature Flight Number:
	- Depature Time:
"""
						save_chat(user_input, response, received_phone_num)

					
					if "Our consultant will contact you to assist" in response:
							agent_handover(user_input, received_phone_num)
							return Response(body, 200)
					

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
			response = "Error occured."
			send_message(response, received_phone_num)
			agent_handover(user_input, received_phone_num)
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

def discard_old_messages(normal_timestamp, Last_message_retrieve_time): 

	#take timestamp of latest message request
	b = Last_message_retrieve_time  > normal_timestamp   #this is a old message. return true. For new message false
	return b

def agent_handling(user_input, received_phone_num, Agent_mode, client_phone_num):
	# if received_phone_num not in AGENT: #It is a client
	print("agent received_phone_num", received_phone_num, Agent_mode)
	if Agent_mode == "on":
		print("agent mode on", Agent_mode)
		#send msg to agent	
		if received_phone_num not in AGENT:  
			print("not in agent", received_phone_num)

			# response = "Now you are in contact with our consultant."
			# send_message(response, received_phone_num)
			# save_chat(user_input, response, received_phone_num)

			response = f"{received_phone_num}, {user_input}"
			send_message(response, AGENT[0])
		#send msg to customer
		if received_phone_num in AGENT:

			response = user_input
			send_message(response, client_phone_num)
			save_chat(user_input, response, client_phone_num)

	if received_phone_num in AGENT:
		if Agent_mode == "off":
			#send msg to customer
			if received_phone_num in AGENT:
				response = f"There is no request from customer yet."
				send_message(response, AGENT[0])

		if "Agent mode off" in user_input: #it is an agent turning off the agent mode after solving the problem.
			client_phone_num = user_input.split(",")[-1].strip()
			query = f"""
	UPDATE user_inputs
	SET Agent_mode = "off"
	WHERE Phone_num = {client_phone_num};
				"""
			update_record(query)
			response = f"Turnned off Agent mode of {client_phone_num}" 
			send_message(response, received_phone_num)  #this msg will send to the agent
			response = "Now you are in contact with bot. Do you want to continue the chat?"
			send_message(response, client_phone_num) #send msg to client
			save_chat(user_input, response, client_phone_num)

	return True


def agent_handover(user_input, received_phone_num):

	#update client table
	query = f"""
UPDATE user_inputs
SET Agent_mode = "on"
WHERE Phone_num = {received_phone_num};
	"""
	update_record(query)

# 	#update agent table 
# 	query = f"""
# UPDATE agent
# SET Client_pno = '{received_phone_num}'
# Where Agent_pno = '{AGENT[0]}'						"""
# 	update_record(query)
# 	print(query)

	#send msg to agent
	#Get previous question
	cols = "message"
	table = "message_store"
	records = get_chat_records(received_phone_num, cols )
	if records:
		message = json.loads(records[-1]["message"])
		prev_question = message["data"]["content"]
	else:
		prev_question = ""

	cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Num_of_kids, Service, Last_message_retrieve_time"
	user_records_updated = get_user_records(received_phone_num, cols )  # retrieve records after updating the extracted values
	summary = json.dumps(user_records_updated)
	response = f"{received_phone_num} wants to contact you.\n\nSummary: {summary}\n\nClient Question: {prev_question}"
	print(response, AGENT[0])
	send_message(response, AGENT[0]) #send msg to agent


	#send messages to client
	response = "Our consultant will contact you to assist."
	save_chat(user_input, response, received_phone_num)
	send_message(response, received_phone_num) 

	return True


if __name__ == '__main__':
	#test server
	# ssl_context_f=('/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/fullchain.pem', '/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/privkey.pem')
	# app.run(ssl_context=ssl_context_f, host='0.0.0.0',port=os.environ.get("PORT", 5000))
	
	# # client server
	# ssl_context_f=('fullchain.pem', 'privkey.pem')
	# app.run(ssl_context=ssl_context_f, host='0.0.0.0',port=os.environ.get("PORT", 5000))
	
	app.run(host='0.0.0.0',port=os.environ.get("PORT", 5000))


