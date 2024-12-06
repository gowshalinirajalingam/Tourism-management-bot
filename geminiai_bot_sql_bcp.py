"""
This code explains creating a whatsapp chatbot using Google Gemini.ai
Here chat history connected to mysql
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
import json 

from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

import sqlite3
from SQL_IUD import get_user_records, get_chat_records, update_record, get_records, get_records_df, getQuesAns
from tools import gen_context, is_valid_email, parse_output_common, parse_output, save_chat, save_to_pdf, get_chat_history



from datetime import datetime
from fuzzywuzzy import process




# Load env variables from .env file
load_dotenv()
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

 # Define LLM model
llm = ChatGoogleGenerativeAI(
model="gemini-1.5-flash-latest",
max_tokens=250,
temperature=0.1,
)

# persist_directory = '/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/Digital tourism whatsapp bot/docs/chroma_predef_trips'

# embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
# vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)


# context, doc_list = gen_context(vectordb, question)
current_date = datetime.now().strftime("%Y-%m-%d")


#Generate answer to the user queries
def llm_common(prompt, history_status, keys):

    keys_str = json.dumps(keys)
    phone_number = keys["received_phone_num"]

    #Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                prompt,
            ),
            ("human", "{inputs}"),
        ]
    )

    chain = prompt | llm 

    # Generate the answer
    ai_msg = chain.invoke({
        "inputs": keys_str
    })

       
    #Retrieve the results
    result= ai_msg.content

    if history_status:
        user_input = keys["user_input"]
        save_chat(user_input, result, phone_number)

    return result

def summarize_chat_history(received_phone_num, user_input):
    print("WELCOME TO SUMMARISE CHAT HISTORY SECTION")

    cols = "message"
    table = "message_store"
    records = get_chat_records(received_phone_num, cols )
    chat_history = get_chat_history(records)
    chat_history.append({"type": "human", "content": user_input}) # add last received msg which is not yet stored in db.

    chat_history_str = json.dumps(chat_history)
    print(chat_history_str)

    prompt = f"""
Extract values of chat_history only.

return the chat history in a text format.
Chat History:
chat_history

**Chat history Summary**:
"""

    history_status = False
    keys = {
        "chat_history":chat_history_str,
        "received_phone_num": received_phone_num
        }
    response = llm_common(prompt, history_status, keys)
    print("summary chat:", response)
    return response


#Generate flow based queries
def flow_bot(user_input, phone_number, user_records_updated):
    print("WELCOME TO FLOW SECTION")
    
    # Define LLM model
#     context = """
# A chatbot is an artificial intelligence program designed to simulate conversation with human users, often through messaging applications or \
# websites. By leveraging natural language processing (NLP) and machine learning algorithms, chatbots can understand and respond to user \
# inquiries in real-time, providing assistance with tasks such as customer support, information retrieval, and transaction facilitation. \
# They can operate 24/7, offering instant responses and improving user engagement while reducing the workload on human agents. With advancements in technology, \
# modern chatbots can maintain context, learn from interactions, and even adapt their tone to match user preferences, creating a more personalized experience. \
# As businesses increasingly adopt chatbots, they are transforming the way companies interact with customers, enhancing efficiency and satisfaction in the digital landscape.
# """

    query = "SELECT * FROM Questions;"
    context = getQuesAns(query)

    chat_summary = summarize_chat_history(phone_number, user_input)
    

    #Create prompt template
    prompt = f"""

Extract values of current_date, user_input, user_records_updatedfrom inputs.

Today's date is current_date. Understand the current the month, year and date to plan the trip. Now, let's proceed with the task...
Role: You are a helpful assistant for planning travel itineraries within Sri Lanka. Your tasks include assisting users in creating travel plans, answering queries, engaging in friendly dialogue, conducting interest assessments, presenting service options, gathering traveler details (adults and kids), confirming quotations, handling booking confirmations (flight details, full name, email), and performing post-booking follow-ups.

chat history: 
Flow of Questions:
    1. **Greeting**: Respond warmly to user greetings and ask how you can assist them today.
    2. **Basic Conversation (Month)**: Gather information on the month for their trip. 
    3. **Basic Conversation (Days)**: Gather information on the number of days for their trip.
    4. **Interest Assessment**: Ask about the traveler’s interests (e.g., Beaches, Wildlife, Culture, etc.).
    5. **Itinerary Planning**: Present the suggested itinerary and ask for user agreement. Output the response exactly as ["Based on your interests here's the suggested itinerary for your trip. Does this look good to you?", "itineraryAPI"].
    6. **Service Options**: Determine the service level required (e.g., driver services, hotel bookings).
    7. **Travelers Information (Adults)**: Ask for the number of adults traveling.
    8. **Travelers Information (Kids)**: Ask for the number of kids traveling.
    9. **Quotation Confirmation**: Output the response exactly as ["I'll send you the quotation for you., "quotationAPI"].
    10. **Booking Confirmation (Flight Details such as Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number)**: Ask for flight details to prepare the invoice.
    11. **Booking Confirmation (Full Name)**: Ask for the full name as per the passport.
    12. **Booking Confirmation (Email)**: Ask for the email address.
    13. **Post-Booking Follow-Up**: Confirm the booking details with a summary of the trip plan and offer additional support by saying that the booking is confirmed and we will send the invoice via email and anything else to help with.

General Instructions:
    • *Response should only contain the question to ask from the user.
    • *Stick to the specified flow and ensure all key areas are covered without unnecessary deviations. Can't skip any of the key areas in the flow.
    • *While generating questions, always consider the already extracted information from **user_records_updated**.
        - **Ensure the following fields are filled before moving to the Itinerary Planning step: Num_of_days, Month.
        - **Ensure the following fields are filled before moving to the Quotation Confirmation step: Service, Num_of_adults, Num_of_kids.
        - **Ensure the following fields are filled before moving to the Booking Confirmation (Full Name) step: Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number.*
    • *Ensure the retrieved information is clearly extracted and properly validated.
    • *Avoid providing an empty response. If the user input is unclear, ask a clarifying question based on the previous interaction.
    • *If the user responds with "I'll provide the details later" or a similar response at any point, respond with: "The details requested are mandatory to proceed. Could you please provide them now?" Do not accept the response and continue until the information is provided.
    • *Do not modify the provided responses for Itinerary Planning and Quotation Confirmation. Send them exactly as they are.
    • *When the user asks a question:
        - **If the question is within the provided context:** 
            {context}
        - **If the question is outside both provided context, respond with:** "I'm currently focused on assisting within the knowledge provided. Do not add any additional questions or text. Let's continue with that."** 
        - **After answering the user’s query, return to the last unanswered question and prompt the user again for their response to ensure the flow continues as intended.**
    • **If the user asks for any modifications to the travel plan or expresses dissatisfaction with the itinerary, respond strictly with: "Our consultant will contact you to assist." Do not add any additional questions or text with the response.** 
"""

    keys = {
        "received_phone_num" : phone_number,
        # "context" : context,
        "current_date" : current_date,
        # "chat_summary" : chat_summary,
        "user_input": user_input,
        "user_records_updated" : user_records_updated
    }

    history_status = True
    result = llm_common(prompt, history_status , keys)

    # #this code is added avoid printing additional text or questions with "Our consultant will contact you to assist."
    # if "Our consultant will contact you to assist." in result:
    #     result = "Our consultant will contact you to assist." 
    return result

#Analyse the intent of the user input
def analyze_intent(user_input, classes ):
    # Define the classes for intent analysis
    text = user_input

 

    print("WELCOME TO INTENT ANALYSIS SECTION")

    # Initialize the LLM

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
          [
              ( "system",
                  f"""
You are a intent classification bot. Classify the text into one of the following categories: {', '.join(classes)}

Current text:
{text}

Instructions:
- The {', '.join(classes)} are in classification priority order.
- output should be the category.
- For the category "Question:, analyze the input based on its structure, punctuation, and phrasing to determine whether it is a question.

Examples for Question:
    "What is the month today?" → Question
    "Can you help me with trip plan" → Question
Examples for Other:
    "1 adults and no kids." → Other
    "The weather is nice today." → Other
  """
              ),
              ("human", "{text}"),
          ]
      )

    # Create chain
    chain = prompt | llm

    # Generate the answer
    ai_msg = chain.invoke({
        "text": text
    })

    # Retrieve the results
    result = ai_msg.content

    return result


#Retrieve_information from the user input and update the db
def retrieve_information(user_input, received_phone_num):
    print("WELCOME TO INFORMATION RETRIEVAL SECTION")

    #Get previous question
    cols = "message"
    table = "message_store"
    records = get_chat_records(received_phone_num, cols )
    if records:
        message = json.loads(records[-1]["message"])
        prev_question = message["data"]["content"]
    else:
        prev_question = ""
        
    classes = ["Name", "Email", "Address", "Num_of_days", "Num_of_adults", "Num_of_kids", "Month", "Start_date", "End_date", "Interests", "Service", "Arrival_date" , "Arrival_time", "Arrival_flight_number", "Depature_date", "Depature_time", "Depature_flight_number"]

    # Initialize the LLM

      # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
          [
              ( "system",
                    """

    - Extract values from information such as classes, received_phone_num, prev_question, user_input, current_date

    Today's date is current_date. Understand the current month, year and date to extract information.
    You are a information retrieval ChatBot. Retrieve the following information of classes from the user_input. 
    To understand the meaning of the user_input refer the previous_question.

    previous_question: prev_question

    Description for information are:
    - 'Name refers to the name of the user.',
    - 'Email refers to the email of the user and the input should be in the default email format.',
    - 'Address refers to the address of the user.',
    - 'Num_of_days refers to how many days users plan to spend on their holiday or trip, and the input should be in numbers.',
    - 'Num_of_adults refers to how many adults plan to stay in a hotel or room, and the input should be in numbers.',
    - 'Num_of_kids refers to how many kids plan to stay in a hotel or room, and the input should be in numbers.',
    - 'Month refers to which month users plan to enjoy their trip or holiday, and the input should be the name of the month.',
    - 'Start_date refers to the day the trip starts, and the input should be in the date format.',
    - 'End_date refers to the day the trip ends, and the input should be in the date format.',
    - 'Interests refers to the user's interests or preferences for the trip (e.g., beach, wildlife, nature, adventure).',
    - 'Service refers to the service customer wants either Driver service only or Driver and Hotel booking services'
    - 'Arrival_date refers to the date that the customer arrives from their airport'.,
    - 'Arrival_time refers to the time that the customer arrives from their airport'.,
    - 'Arrival_flight_number refers to the flight number that the customer arrives from their airport'.,
    - 'Depature_date refers to the date that the customer depart in Sri Lanka'.,
    - 'Depature_time refers to the time that the customer depart in Sri Lanka'.,
    - 'Depature_flight_number refers to the flight number that the customer depart in Sri Lanka'.,



    Current input:
    user_input

    Example conversation:
        previous_question: How many days are you planning for the trip?
        user_input: 10
        output: 
        UPDATE user_inputs
        SET Num_of_days = "10"
        WHERE Phone_num = 46546;

        previous_question: How many adults are joining your trip?
        user_input: it is 2.
        output: 
        UPDATE user_inputs
        SET Num_of_adults = "2"
        WHERE Phone_num = 46546;


    Output format should be a JSON: You will respond to the input by producing two outputs in a JSON format.
    {{"intent_of_prev_question": identify the intent of previous question and output the respective information, "query":"UPDATE user_inputs SET Name = 'John', Email = 'john@gmail.com', Address = 'Swiss', Num_of_days = '7', Num_of_adults = '10', Num_of_kids = '2', Month = 'june', Start_date = '2024/10/10', End_date = '2024/10/20', Interests = 'nature and beaches', Service = 'Driver and hotel booking', Arrival_date = ' 03rd October 2024', Arrival_time = '16:35', Arrival_flight_number = 'FZ 549' , Depature_date = '11 October 2024', Depature_time = '17:30', Depature_flight_number = 'FZ 550' WHERE Phone_num = received_phone_num;"}}

    **Instructions:**
    - Carefully consider the prev_question and the user_input to determine if the user_input contains relevant information.
    - If the user_input does not directly answer or match the context of the prev_question, output "" for that information. Do not extract or assume any values that do not fit the context.
    - While retrieving only retrieve information from user_input that matches the context of the prev_question. If any information doesn't match, just output SELECT 1 FROM user_inputs.
    - In the output only change the line starts with SET.
    - The output should be strictly in given format and avoid unnecessary words.
    - If the keys in line SET doesn't have values please remove those keys.
    - If all of the keys doesn't have values just output SELECT 1 FROM user_inputs;
    - If any service found in the user_input only please classify it in to one of the two categories such as Driver, Driver and Hotel. Else send SELECT 1 FROM user_inputs; as response and ask the question again to retrieve service information. 
    - If you find number of kids and it is in text format, Convert it into number. Example: "No kids" means 0.
    - Take user inputs as integers when you receive Num_of_days, Num_of_adults, and Num_of_kids.

   """
              ),
              ("human", "{information}"),
          ]
      )

   # Create chain
    chain = prompt | llm

    keys = {
        "user_input": user_input,
        "prev_question": prev_question,
        "received_phone_num": received_phone_num,
        "classes": f"{', '.join(classes)}",
        "current_date": current_date
    }
    keys_str = json.dumps(keys)

    # Generate the answer
    ai_msg = chain.invoke({
        "information": keys_str
    })

    # Retrieve the results
    result = ai_msg.content
    
    pattern = r'```json\n(.*?)\n```'
    group = 1
    json_retrieved_string = parse_output_common(result, pattern, group)
    print("json_retrieved_string:",json_retrieved_string)

    json_retrieved = json.loads(json_retrieved_string)

    retrieved_information = json_retrieved['query']
    retrieved_information = parse_output(retrieved_information, received_phone_num)

    intent_of_prev_question = json_retrieved['intent_of_prev_question'] 

    update_record(retrieved_information)
    
    return intent_of_prev_question 

#Send the quotation and hotel list to the user
def send_quotation(received_phone_num):
    pdf_path_hotel = None
    columns = "Num_of_days, Num_of_adults, Num_of_kids, Service, Month"

    records = get_user_records(received_phone_num, columns)

    Num_of_days = records[0]["Num_of_days"]
    Num_of_adults = records[0]["Num_of_adults"]
    Num_of_kids = records[0]["Num_of_kids"]
    Service = records[0]["Service"]
    Month = records[0]["Month"]


    keys = {
            "days": Num_of_days,
            "Num_of_adults": Num_of_adults,
            "Num_of_kids": Num_of_kids,
            "pax" : int(Num_of_adults) + int(Num_of_kids),
            "Month": Month
        }
    print(keys)


    
    if "otel" in Service: #Means Driver and Hotel Booking
        pdf_path_hotel = "Hotel_rates_output_pdf/"+received_phone_num+".pdf"
        hotel_cost, room_type = hotel_cost_calculation(keys)
        hotel_price_list_generation(keys, pdf_path_hotel, hotel_cost, room_type) #save pdf
        response = driver_quotation_calculation_hotel(keys, hotel_cost)

        if int(Num_of_kids) > 0:
            response = "*Hotels + English Speaking Tourist Driver*\n\n"+ response +"\n\n"+ "Please find the hotel details and price. \nThere will a slight change in the provided details as kids are included."
        else:
            response = "*Hotels + English Speaking Tourist Driver*\n\n"+ response +"\n\n"+ "Please find the hotel details and price."
    else:
        response = driver_quotation_calculation_driver(keys ) 
        response = "*English Speaking Tourist Driver*\n\n"+ response

    return response, pdf_path_hotel

#Driver cost calculation
def driver_quotation_calculation_driver(keys):
    print("WELCOME TO QUOTATION CALCULATION SECTION")

    # Initialize the LLM

    # Define the price charts

    keys_str = json.dumps(keys)

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", f"""
                'You are a text-based Trip Plan Quotation Calculation ChatBot. Choose the trip plan cost, km, extra rate and vehicle based on the number of passengers, the number of days and month provided in the information'
                 
                Description of information:
                - 'days': The number of days for which the service is required.
                - 'pax': The number of passengers.
                - 'Month' : The month of trip.
                - 'Winter': This refers to the months of November, December, January, February, March, and April. If a user selects any of these months, classify it as Winter.
                - 'Summer': This refers to the months of May, June, July, August, September, and October. If a user selects any of these months, classify it as Summer.

             
                Note: 5Pax refers to "5 passengers."
             
                output format:
                    "SELECT (SELECT "5Pax" FROM Transport_table WHERE days = 6 AND Season = "Winter") AS "driver_cost", (SELECT Kilometers FROM Transport_table WHERE Season = "Winter" AND days = 6) AS "km", (SELECT ExtraRate FROM transport_extra_vehicle WHERE Pax = 5) AS "extra_rate", (SELECT Vehicle FROM transport_extra_vehicle WHERE Pax = 5) AS "vehicle";"

                Instructions:
                - In the output only change the line starts with SELECT.
                - The output should be strictly in given format and avoid unnecessary words.
                - If the keys in line SELECT doesn't have values please remove those keys.

            """),
            ("human", "{information}"),
        ]
    )

    # Create chain
    chain = prompt | llm

    # Generate the answer
    ai_msg = chain.invoke({"information": keys_str})
    response = ai_msg.content.strip()
    print(response)

    group = 0
    pattern = r'\bSELECT\b.*?;'
    response = parse_output_common(response, pattern, group)

    records = get_records(response)  #[{'cost': 535, 'km': 850, 'extra_rate': 110, 'vechile': 'FLATROOF VAN'}]  
    print(records)
    cost = int(records[0]["driver_cost"])
    km = int(records[0]["km"])
    extra_rate = int(records[0]["extra_rate"])
    vehicle = records[0]["vehicle"]
    per_person_cost = int(cost/int(keys["pax"]))
    



    response = f"""
It’s *{cost}USD* for {keys["days"]} days for {keys["Num_of_adults"]} adults and {keys["Num_of_kids"]} kids. 
_(Per person {per_person_cost} USD)_

_[Price given is for {km} kms, if exceeded {extra_rate} LKR per km to be paid]_
_[You can have a {vehicle}]_


*Inclusions*
•       Pick up & Drop off from Airport
•       English Speaking Tourist driver
•       Air Conditioning Car
•       Fuel Cost
•       Meals & accommodation for the driver
•       Parking fees, toll fees, Highway Charges
•       All government taxes

*Exclusions*
•       Hotel accommodation
•       Meals & beverages during the tour
•       Entry tickets to Archaeological sites, museums, National Parks etc.
•       Jeep safaris, village tours (can be arranged by us upon confirmation)
•       Transport to Horton Plains National Park (if applicable)
•       Train ticket https://seatreservation.railway.gov.lk/mtktwebslr/ (tickets get released 30 days before the train date)
•       Visa fees - Guests need to apply visa online through https://www.srilankaevisa.lk/index.html
•       Tips & Portages
•       Airfare and airport embarkation tax (included in air ticket)
•       Other extras of personal nature such as alcoholic/ non alcoholic drinks, laundry, telephone calls, photo and video camera permits
•       Services others than specified above
"""
    
    return response

#Driver cost calculation
def driver_quotation_calculation_hotel(keys, total_hotel_cost):
    print("WELCOME TO QUOTATION CALCULATION SECTION")

    # Initialize the LLM

    # Define the price charts

    keys_str = json.dumps(keys)

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", f"""
                'You are a text-based Trip Plan Quotation Calculation ChatBot. Choose the trip plan cost, km, extra rate and vehicle based on the number of adults, the number of kids the number of days and month provided in the information'
                 
                Description of information:
                - 'days': The number of days for which the service is required.
                - 'pax': The number of passengers. It should be the sum of Num_of_adults and Num_of_kids.
                - 'Month' : The month of trip.
                - 'Winter': This refers to the months of November, December, January, February, March, and April. If a user selects any of these months, classify it as Winter.
                - 'Summer': This refers to the months of May, June, July, August, September, and October. If a user selects any of these months, classify it as Summer.

             
                Note: 5Pax refers to "5 passengers."
             
                output format:
                    "SELECT (SELECT Kilometers FROM Transport_table WHERE Season = "Winter" AND days = 6) AS "km", (SELECT ExtraRate FROM transport_extra_vehicle WHERE Pax = 5) AS "extra_rate", (SELECT Vehicle FROM transport_extra_vehicle WHERE Pax = 5) AS "vehicle";"

                Instructions:
                - In the output only change the line starts with SELECT.
                - The output should be strictly in given format and avoid unnecessary words.
                - If the keys in line SELECT doesn't have values please remove those keys.

            """),
            ("human", "{information}"),
        ]
    )

    # Create chain
    chain = prompt | llm

    # Generate the answer
    ai_msg = chain.invoke({"information": keys_str})
    response = ai_msg.content.strip()
    print(response)

    group = 0
    pattern = r'\bSELECT\b.*?;'
    response = parse_output_common(response, pattern, group)

    records = get_records(response)  #[{'cost': 535, 'km': 850, 'extra_rate': 110, 'vechile': 'FLATROOF VAN'}]  
    print(records)

    cost = total_hotel_cost
    km = int(records[0]["km"])
    extra_rate = int(records[0]["extra_rate"])
    vehicle = records[0]["vehicle"]
    per_person_cost = int(cost/int(keys["Num_of_adults"]))
    



    response = f"""
It’s *{cost}USD* for {keys["days"]} days for {keys["Num_of_adults"]} adults and {keys["Num_of_kids"]} kids.
_(Per person {per_person_cost} USD)_

_[Price given is for {km} kms, if exceeded {extra_rate} LKR per km to be paid]_
_[You can have a {vehicle}]_

*Inclusions*
•       Pick up & Drop off from Airport
•       English Speaking Tourist driver
•       Air Conditioning Car
•       Fuel Cost
•       Meals & accommodation for the driver
•       Parking fees, toll fees, Highway Charges
•       All government taxes
•       Hotel accommodation


*Exclusions*
•       Meals & beverages during the tour
•       Entry tickets to Archaeological sites, museums, National Parks etc.
•       Jeep safaris, village tours (can be arranged by us upon confirmation)
•       Transport to Horton Plains National Park (if applicable)
•       Train ticket https://seatreservation.railway.gov.lk/mtktwebslr/ (tickets get released 30 days before the train date)
•       Visa fees - Guests need to apply visa online through https://www.srilankaevisa.lk/index.html
•       Tips & Portages
•       Airfare and airport embarkation tax (included in air ticket)
•       Other extras of personal nature such as alcoholic/ non alcoholic drinks, laundry, telephone calls, photo and video camera permits
•       Services others than specified above
"""
    
    return response


#Hotel cost calculation
def hotel_cost_calculation(keys):
    print("WELCOME TO HOTEL COST CALCULATION SECTION")

    # Initialize the LLM

    # Define the price charts

    keys_str = json.dumps(keys)

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", f"""
                'You are a text-based Trip Plan hotel cost Calculation ChatBot. Choose the hotel cost, based on the number of adults, the number of days and month provided in the information'
                 
                Description of information:
                - 'days': The number of days for which the service is required.
                - 'Num_of_adults': The number of adults.
                - 'Month' : The month of trip.
                - 'Winter': This refers to the months of November, December, January, February, March, and April. If a user selects any of these months, classify it as Winter.
                - 'Summer': This refers to the months of May, June, July, August, September, and October. If a user selects any of these months, classify it as Summer.

                Note: 5adults refers to "5 Adults."

                output format:
                    "SELECT(SELECT "5Adults" FROM Hotel_rates WHERE days = "6" AND Months LIKE '%March%') AS "hotel_cost", (SELECT "Room" FROM Rooms WHERE Adults = 5) AS "room_type";"

                Instructions:
                - In the output only change the line starts with SELECT.
                - The output should be strictly in given format and avoid unnecessary words.
                - If the keys in line SELECT doesn't have values please remove those keys.
             

            """),
            ("human", "{information}"),
        ]
    )

    # Create chain
    chain = prompt | llm

    # Generate the answer
    ai_msg = chain.invoke({"information": keys_str})
    response = ai_msg.content.strip()
    print(response)

    group = 0
    pattern = r'\bSELECT\b.*?;'
    response = parse_output_common(response, pattern, group)

    records = get_records(response)  #[{'cost': 535, 'km': 850, 'extra_rate': 110, 'vechile': 'FLATROOF VAN'}]  
    print(records)

    room_type = records[0]["room_type"]
    hotel_cost = int(records[0]["hotel_cost"])

    return hotel_cost, room_type

#Generate pdf with hotel list
def hotel_price_list_generation(keys, pdf_path_hotel, hotel_cost, room_type):
    print("WELCOME TO HOTEL PRICE AND PDF GENERATION")

    # Initialize the LLM

    # Define the price charts

    keys_str = json.dumps(keys)
    print("keys",keys)
    Num_of_adults = int(keys["Num_of_adults"])

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", f"""
                'You are a information retrieval ChatBot. Retrieve the following information based on the number of days and month provided in the information.'
             
                Description of information:
                - 'Month' : The month of trip.
                - 'Package': The number of days for which the service is required.
                - 'Winter': This refers to the months of November, December, January, February, March, and April. If a user selects any of these months, classify it as Winter.
                - 'Summer': This refers to the months of May, June, July, August, September, and October. If a user selects any of these months, classify it as Summer.


                output format:
                    "SELECT * FROM Hotel_Details WHERE Package = "5" AND Season = "Winter";"

                Insatructtions:
                - Consider the previous question and user inputs while retrieving the information.
                - In the output only change the line starts with SELECT.
                - The output should be strictly in given format and avoid unnecessary words.
                - If the keys in line SELECT doesn't have values please remove those keys.

            """),
            ("human", "{information}"),
        ]
    )

    # Create chain
    chain = prompt | llm

    # Generate the answer
    ai_msg = chain.invoke({"information": keys_str})
    response = ai_msg.content.strip()  

    group = 0
    pattern = r'\bSELECT\b.*?;'
    response = parse_output_common(response, pattern, group)
    print(response)
    df = get_records_df(response)
    save_to_pdf(df, pdf_path_hotel, hotel_cost, room_type, Num_of_adults)

    
    return response

#Validate user inputs 
def validate_inputs(intent_of_prev_question, user_input, user_records_updated, received_phone_num):

    # Validate month
    if intent_of_prev_question == "Month":
        month = user_records_updated[0]["Month"]

        if month:
            valid_months = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            
            
            # Find the closest match from valid_months
            closest_match, score = process.extractOne(month, valid_months)
            
            # Define a threshold score for considering a match valid
            threshold = 80  # You can adjust this threshold
            
            if score < threshold:
                error_msg = "Couldn't identify a month from your input. Can you provide a valid month?"
                print(error_msg)
                save_chat(user_input, error_msg, received_phone_num)
                return False, error_msg
            else:  # The database hase only values for temp_months. So the user input should be inside that.
                temp_months = [ "January", "February", "March", "April", "September", "October", "November", "December"]
                
                # Find the closest match from valid_months
                closest_match, score = process.extractOne(month, temp_months)
                
                # Define a threshold score for considering a match valid
                threshold = 80  # You can adjust this threshold
                
                if score < threshold:
                    error_msg = "Can you provide months from Jan-Apr or Sep-Dec? We are working on the month you provided."
                    print(error_msg)
                    save_chat(user_input, error_msg, received_phone_num)
                    return False, error_msg
        else:
                error_msg = "Please provide the month that you are planning to travel."
                print(error_msg)
                save_chat(user_input, error_msg, received_phone_num)
                return False, error_msg
    
    # Validate num_of_days
    if intent_of_prev_question == "Num_of_days":
        days = user_records_updated[0]["Num_of_days"]

        print("days:",days)

        if days:
            try:
                days = int(days)
                if days <= 4 or days > 14:
                    error_msg = "The number of travelling days should be in between 5 to 14."
                    print(error_msg)
                    save_chat(user_input, error_msg, received_phone_num)
                    return False, error_msg
            except ValueError:
                error_msg = "The number of travelling days must be a valid integer."
                print(error_msg)
                save_chat(user_input, error_msg, received_phone_num)
                return False, error_msg
        else:
            error_msg = "Please provide the number of days that you are travelling."
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg
    
    # Validate num_of_adults
    if intent_of_prev_question == "Num_of_adults":
        pax = user_records_updated[0]["Num_of_adults"]

        if pax:
            try:
                pax = int(pax)
                if pax <= 0 or pax > 5:
                    error_msg = "The number of persons (pax) should be 5 or less and greater than 0."
                    print(error_msg)
                    save_chat(user_input, error_msg, received_phone_num)
                    return False, error_msg
            except ValueError:
                error_msg = "The number of persons (pax) must be a valid integer."
                print(error_msg)
                save_chat(user_input, error_msg, received_phone_num)
                return False, error_msg
        else:
            error_msg = "Please provide the number of adults who are travelling."
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg
    
    
    # Validate num_of_kids
    if intent_of_prev_question == "Num_of_kids":
        kids = user_records_updated[0]["Num_of_kids"]

        if kids:
            try:
                kids = int(kids)
            except ValueError:
                error_msg = "The number of kids must be a valid integer."
                print(error_msg)
                save_chat(user_input, error_msg, received_phone_num)
                return False, error_msg
        else:
            error_msg = "Please provide the number of kids that you are travelling."
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg
    
    
    # Validate email
    if intent_of_prev_question == "Email":
        email = user_records_updated[0]["Email"]

        if email:
            if not is_valid_email(email):
                    error_msg = "The email is invalid. Please provide a valid email address"
                    print(error_msg)
                    save_chat(user_input, error_msg, received_phone_num)
                    return False, error_msg
        else:
            error_msg = "Please provide your email address."
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg
        
    # Validate name
    if intent_of_prev_question == "Name":
        name = user_records_updated[0]["Name"]

        # If the user didn't provide the name it will send a error message. We can add validation part in future.
        if not name:
            error_msg = "Please provide your email address."
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg

    if "screenshot" in intent_of_prev_question or "flight" in intent_of_prev_question:
        print("take the screen shot")
        #TODO
    
    
           
        
    success_msg = "Valid input."
    return True, success_msg

