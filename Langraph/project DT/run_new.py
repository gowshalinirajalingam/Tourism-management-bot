

"""
Main Code
"""

from graph import create_graph, compile_workflow, save_workflow

from flask import Flask, request, Response, jsonify
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import json
import traceback
import ast
from datetime import datetime

from tools.ToolsSQL import get_user_records, update_record, delete_record, get_media_id, get_chat_records
from tools.ToolsLLM import save_chat, get_chat, convert_to_conversation_format

# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import sqlite3

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.environ["GOOGLE_API_KEY"]
# OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
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

server = 'gemini'
# server = 'openai'
model = 'gemini-1.5-flash'
# model = 'gpt-4o'
key = GEMINI_API_KEY
memory = False
verbose = True


print("Creating graph and compiling workflow...")
graph = create_graph(server=server, model=model, temperature=0.5, max_tokens=50, key=key)
workflow = compile_workflow(graph, memory=memory)
save_workflow(workflow)
print("Graph and workflow created.")


#WHatsapp business API platform - Twillio
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
			response = "Error occured, Our consultant will contact you to assist"
			send_message(response, received_phone_num)
			# body = request.values
			return Response(body, 200)
			
    
	if request.method == 'POST':
		try:
			
			body = request.values
			user_input = request.values.get('Body', '').lower()

			if "MessageType" in request.values:
				
				print("user_input ::", user_input)

				received_phone_num = request.values.get("WaId", "")

				# Generate Unix epoch timestamp
				# Since Twilio does not send a timestamp directly, you can use the current time
				timestamp = int(datetime.now().timestamp())  # Get current time in Unix epoch
				print("Current Unix Epoch Timestamp: ", timestamp) #this is unix timestamp
				normal_timestamp = datetime.fromtimestamp(int(timestamp))				#this is normal time stamp
				response = ''

				print("Receipient Phone Number:",received_phone_num)

				# if received_phone_num in PHONE_NUMBER or received_phone_num in AGENT:
				if received_phone_num:

					#Validate input type
					input_type = request.values.get("MessageType", "")
					if  input_type != 'text':
						response = f"The {input_type} is not supported at the moment"
						send_message(response, received_phone_num)
						return Response(body, 200)
				
					

					#If the input type is text proceed
					user_input = user_input
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

						#notify agent if new user comes
						response = f"{received_phone_num} is starting a new conversation now."
						send_message(response, AGENT[0])  #this msg will send to the agent

					print("user_records",user_records)

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
						print("Response: ", response)
						return Response(body, 200)
					
					
					#Stop/ Start chat after connecting with agent
						#Get agent mode from the data base
					cols = "Agent_mode"
					user_records_updated = get_user_records(received_phone_num, cols )  #for the first time the user_records will be empty. so have to retrieve again after insertion.
					Agent_mode = user_records_updated[0]["Agent_mode"]

					if Agent_mode == "on" or received_phone_num in AGENT:
						agent_handling(user_input, received_phone_num, Agent_mode)
						return Response(body, 200)
					

					

					if not response.strip():  # This checks for empty strings, None, or other falsy values
						print("Error: The response is blank or contains only whitespace.",response,"!")
						response = "The answer you provided is unclear or potentially harmful. Can you provide in another way?"
						# save_chat(user_input, response, received_phone_num)

					#LANGGRAPH START
					pdf_path_hotel = None
					

					dict_inputs = {"input": user_input,"received_phone_num": received_phone_num}
					config = {"configurable": {"thread_id": "1"}}

					if memory:
						for event in workflow.stream(
							dict_inputs,config
							):
							if verbose:
								print("\nState Dictionary:", event)
								for value in event.values():
									if "bot_response" in value:
										response = value.get("bot_response")
									if "HotelPriceListGenerator_response" in value:
										pdf_path_hotel = value.get("HotelPriceListGenerator_response")
							else:
								print("\n")
					else:
						for event in workflow.stream(
							dict_inputs
							):
							if verbose:
								print("\nState Dictionary:", event)
								for value in event.values():
									if "bot_response" in value:
										response = value.get("bot_response")
									if "HotelPriceListGenerator_response" in value:
										pdf_path_hotel = value.get("HotelPriceListGenerator_response")


							else:
								print("\n")
                    #LANGGRAPH END
					if not response.strip():  # This checks for empty strings, None, or other falsy values
						print("Error: The response is blank or contains only whitespace.")
						response = "The answer you provided is unclear. Can you provide in another way?"
						# save_chat(user_input, response, received_phone_num)

					
					print("response:",response)
					print("response:",type(response))


					#Send Itinerary plan pdf
					if "itineraryAPI" in response:
						cols = "Name, Email, Num_of_days, Month, Interests, Num_of_adults, Num_of_kids, Service, Last_message_retrieve_time"
						user_records = get_user_records(received_phone_num, cols )

						days = user_records[0]["Num_of_days"]
						month = user_records[0]["Month"]

						output = send_itinerary_pdf_to_whatsapp(received_phone_num, days, month)
						print(output)
						# save_chat(user_input, output, received_phone_num)

						return Response(body, 200)
					
					#Send Quotation details and pdf
					elif pdf_path_hotel:
						send_hotel_list_and_price_pdf_to_whatsapp(received_phone_num, pdf_path_hotel)

					
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
			elif "SmsStatus" in body:
				read_status = request.values("SmsStatus", "")
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
			response = "Error occured, Our consultant will contact you to assist"
			received_phone_num = request.values.get("WaId", "")
			user_input = body
			print("received_phone_num :", received_phone_num)
			send_message(response, received_phone_num)
			agent_handover(user_input, received_phone_num)
			return Response(body, 200)



def send_itinerary_pdf_to_whatsapp( received_phone_num, days, month, from_whatsapp_number=None):
	print("days :",days, "month :",month)
	records = get_media_id(days, month)
	print("records :", records)
	media_id = records[0]["media_id"]
	print("media_id", media_id)
	output = "Based on your interests here's the suggested itinerary for your trip. Does this look good to you?"

	# #send file from whatsapp media
	# url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
	# headers = {
	# 	f"Authorization": f"Bearer {WHAT_TOKEN}",
	# 	"Content-Type": "application/json"
	# }
	# data = {
	# 	"messaging_product": "whatsapp",
	# 	"to": received_phone_num,
	# 	"type": "document",

	# 	"document": {          
	# 			"id": media_id,
	# 			"caption": output, 
	# 			"filename": "itinerary.pdf"
	# 			}
	# }

	# response = requests.post(url, json=data, headers=headers)  #send msg to whatsapp
	# print("itinerary pdf status:",response.text)
	# return output
	"""Send a WhatsApp message to the specified phone number."""
	if from_whatsapp_number is None:
		from_whatsapp_number = os.getenv('TWILIO_PHONE_NUMBER_ID')  # Fetch from environment variable
	to_whatsapp_number = f'whatsapp:+{received_phone_num}'

	# Send the message
	message = client.messages.create(
		body=output,
		media_url=[
			f"https://drive.google.com/uc?export=download&id={media_id}"
		],

		from_=from_whatsapp_number,
		to=to_whatsapp_number
	)
	print("message :", message)
	print(output)
	return message.sid


def send_hotel_list_and_price_pdf_to_whatsapp(received_phone_num, pdf_path_hotel, from_whatsapp_number=None):
	"""Send a WhatsApp message to the specified phone number."""
	output = f"These are the hotel list with price details."

	hotel_media_id = upload_hotel_list(pdf_path_hotel).strip()
	print("pdf_path_hotel media_id :", hotel_media_id)

	# #send file from whatsapp media
	# url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
	# headers = {
	# 	f"Authorization": f"Bearer {WHAT_TOKEN}",
	# 	"Content-Type": "application/json"
	# }
	# data = {
	# 	"messaging_product": "whatsapp",
	# 	"to": received_phone_num,
	# 	"type": "document",

	# 	"document": {          
	# 			"id": media_id,
	# 			"caption": output, 
	# 			"filename": "hotel_list.pdf"
	# 			}
	# }

	# response = requests.post(url, json=data, headers=headers)  #send msg to whatsapp
	# print("hotel list pdf status:",response.text)
	# # return output
	# return media_id
	if from_whatsapp_number is None:
		from_whatsapp_number = os.getenv('TWILIO_PHONE_NUMBER_ID')  # Fetch from environment variable
	to_whatsapp_number = f'whatsapp:+{received_phone_num}'

	# Send the message
	message = client.messages.create(
		body=output,
		media_url=[
			f"https://drive.google.com/uc?export=download&id={hotel_media_id}"
		],

		from_=from_whatsapp_number,
		to=to_whatsapp_number
	)
	print("hotel message :", message)
	print(output)
	return message.sid


# def upload_hotel_list(pdf_path_hotel):

# 	url = 'https://graph.facebook.com/v20.0/'+PHONE_NUMBER_ID+'/media'
# 	headers = {
# 		'Authorization': f'Bearer {WHAT_TOKEN}',
# 	}
# 	f = open(pdf_path_hotel, "rb")
# 	files = {
# 		'file':(os.path.basename(f.name), f, 'application/pdf'),
# 		'type': (None, "pdf"),
# 		'messaging_product': (None, "whatsapp"),
# 	}

# 	response = requests.post(url, headers=headers, files=files)
# 	r = response.text
# 	media_id = json.loads(r)["id"]

# 	return media_id

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Set your credentials file and scopes
SERVICE_ACCOUNT_FILE = 'gen-lang-client-0573734709-f510a6adfa61.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
PARENT_FOLDER_ID = '1dYBFZpKUVji56Qz3U4cy5So-B2lPhuD3'  # Replace with the ID of the folder you want to upload to

def authenticate():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def upload_hotel_list(file_path):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)
    
    file_name = os.path.basename(file_path)

    # Search for a file with the same name in the specified folder
    query = f"'{PARENT_FOLDER_ID}' in parents and name='{file_name}'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    # If the file exists, delete it
    if items:
        for item in items:
            print(f'Deleting existing file: {item["name"]} ({item["id"]})')
            service.files().delete(fileId=item['id']).execute()

    # Upload the new file
    file_metadata = {
        'name': file_name,
        'parents': [PARENT_FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    hotel_media_id = file.get("id")
    print(f'File ID: {hotel_media_id} uploaded successfully.')
    return hotel_media_id

def get_current_date_time():
	from datetime import datetime

	# Get the current date and time
	now = datetime.now()
	formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

	formatted_now
	return formatted_now

# def send_message(response, received_phone_num):
# 	url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
# 	headers = {
# 		f"Authorization": f"Bearer {WHAT_TOKEN}",
# 		"Content-Type": "application/json"
# 	}
# 	data = {
# 		"messaging_product": "whatsapp",
# 		"to": received_phone_num,
# 		"type": "text",
# 		"text": {"body": response}
# 	}

# 	response = requests.post(url, json=data, headers=headers)  #send msg to whatsapp
    
# def send_message(response, received_phone_num):
#     """Respond to incoming calls with a simple text message."""

#     # Start our TwiML response
#     resp = MessagingResponse()

#     resp.message(response)

#     return str(resp)

from twilio.rest import Client

# Your Twilio account SID and Auth Token
ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

# Twilio client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_message(response, received_phone_num, from_whatsapp_number=None):
	"""Send a WhatsApp message to the specified phone number."""
	if from_whatsapp_number is None:
		from_whatsapp_number = os.getenv('TWILIO_PHONE_NUMBER_ID')  # Fetch from environment variable
	
	to_whatsapp_number = f'whatsapp:+{received_phone_num}'
	print("to_whatsapp_number :", to_whatsapp_number)

	# Send the message
	message = client.messages.create(
		body=response,
		from_=from_whatsapp_number,
		to=to_whatsapp_number
	)
	return message.sid


def discard_old_messages(normal_timestamp, Last_message_retrieve_time): 

	#take timestamp of latest message request
	b = Last_message_retrieve_time  > normal_timestamp   #this is a old message. return true. For new message false
	return b

@app.route('/agenthandle', methods=['POST']) # agent_handle() was added for the purpose of turn off the agent mode by using postman
def agent_handle():
    # Get the JSON data from the request
    data = request.get_json()

    # Extract required fields from the JSON data
    user_input = data.get('user_input')
    received_phone_num = data.get('received_phone_num')
    Agent_mode = data.get('Agent_mode')

    # Call the agent_handling function with the extracted data
    result = agent_handling(user_input, received_phone_num, Agent_mode)

    # Return a response
    return jsonify({"status": "success", "result": result})


def agent_handling(user_input, received_phone_num, Agent_mode):
	# if received_phone_num not in AGENT: #It is a client

	#send msg to client	
	if Agent_mode == "on" and received_phone_num not in AGENT:
		response = "Now you are in contact with our consultant."
		send_message(response, received_phone_num)
		save_chat(user_input, response, received_phone_num)

		
	if received_phone_num in AGENT and "agent mode off" in user_input.lower(): #it is an agent turning off the agent mode after solving the problem.
		client_phone_num = user_input.split(",")[-1]
		client_phone_num = client_phone_num.replace(" ", "")
		print("client_phone_num :",client_phone_num)
		query = f"""

UPDATE user_inputs
SET Agent_mode = "off"
WHERE Phone_num = {client_phone_num};
			"""
		update_record(query)
		response = f"Turnned off Agent mode of {client_phone_num}" 
		send_message(response, received_phone_num)  #this msg will send to the agent
		response = "Now we can start the conversation. Do you want to continue the chat?"
		send_message(response, client_phone_num) #send msg to client
		save_chat(user_input, response, client_phone_num)
	
	elif received_phone_num in AGENT:   #Agent can't involve in bot communication
		response = "You can't talk with bot."
		send_message(response, received_phone_num) 

	return True


# @app.route('/agenthandle', methods=['POST'])
# def agent_handling(user_input, received_phone_num, Agent_mode):
#     # Get data from the request body
#     data = request.get_json()
    
#     user_input = data.get('user_input')
#     received_phone_num = data.get('received_phone_num')
#     Agent_mode = data.get('Agent_mode')

#     # Send msg to client    
#     if Agent_mode == "on" and received_phone_num not in AGENT:
#         response = "Now you are in contact with our consultant."
#         send_message(response, received_phone_num)
#         save_chat(user_input, response, received_phone_num)

#     if received_phone_num in AGENT and "agent mode off" in user_input.lower():  # it is an agent turning off the agent mode after solving the problem.
#         client_phone_num = user_input.split(",")[-1].strip()
#         print("client_phone_num:", client_phone_num)
#         query = f"""
#         UPDATE user_inputs
#         SET Agent_mode = "off"
#         WHERE Phone_num = '{client_phone_num}';
#         """
#         update_record(query)
#         response = f"Turned off Agent mode of {client_phone_num}" 
#         send_message(response, received_phone_num)  # this msg will send to the agent
#         response = "Now we can start the conversation. Do you want to continue the chat?"
#         send_message(response, client_phone_num)  # send msg to client
#         save_chat(user_input, response, client_phone_num)
    
#     elif received_phone_num in AGENT:  # Agent can't involve in bot communication
#         response = "You can't talk with bot."
#         send_message(response, received_phone_num) 

#     return "success"
# curl --location 'http://localhost:5000/agenthandle' \
# --header 'Content-Type: application/json' \
# --data '{
#     "user_input": "agent mode off, 94768503821",
#     "received_phone_num": "94768503822",
#     "Agent_mode": "on"
# }'


def agent_handover(user_input, received_phone_num):
	#Freeze whatsapp and send msg our consultant will contact u.
	query = f"""
UPDATE user_inputs
SET Agent_mode = "on"
WHERE Phone_num = {received_phone_num};
	"""
	update_record(query)

	#send messages to client
	response = "Our consultant will contact you to assist."
	save_chat(user_input, response, received_phone_num)
	send_message(response, received_phone_num) 

	#send msg to agent
	#Get previous conversations
	messages = get_chat(received_phone_num)
	try:
		# previous_conversations = messages[-6:]
		previous_conversations = messages

	except:
		previous_conversations = ""
	previous_conversations = convert_to_conversation_format(previous_conversations)
	
	
	response = f"{received_phone_num} wants to contact you.\n\nChat history: {previous_conversations}"
	print(response, AGENT[0])
	send_message(response, AGENT[0]) #send msg to agent

	return True



if __name__ == '__main__':
	# #test server
	# ssl_context_f=('/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/fullchain.pem', '/etc/letsencrypt/live/digitaltourismbot.senzmatica.com/privkey.pem')
	# app.run(ssl_context=ssl_context_f, host='0.0.0.0',port=os.environ.get("PORT", 5000))
	
	# # client server
	# ssl_context_f=('fullchain.pem', 'privkey.pem')
	# app.run(ssl_context=ssl_context_f, host='0.0.0.0',port=os.environ.get("PORT", 5000))
	
	app.run(host='0.0.0.0',port=os.environ.get("PORT", 5000))

