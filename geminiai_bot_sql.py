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
from tools import gen_context, is_valid_email, parse_output_common, parse_output, save_chat, save_to_pdf


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

#Generate answer to the user queries
def answer_common_questions(question, phone_number):
    print("WELCOME TO Q&A SECTION")

    # Define LLM model

    #Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
Today's date is {current_date}. Understand the current month, year, and date to answer questions. Now, let's proceed with the task...
You are a knowledgeable assistant. Your task is to answer user questions only about the country Sri Lanka and the following specific topics:
    1. Weather: Provide current weather information, forecasts, and related details specific to Sri Lanka only.
    2. Trains: Offer information about train schedules, routes, ticket availability, and other train-related queries within Sri Lanka only.
    3. Foods and Restaurants: Provide information about popular foods, restaurants, and dining options in Sri Lanka. Include details about types of cuisine, notable restaurants, and dining experiences in Sri Lanka only.
    4. Tourist Places: Offer information about tourist attractions, landmarks, and points of interest in Sri Lanka only. Provide details on popular destinations, activities, and travel tips related to Sri Lanka.
    5. Default Response for Trip Planning: If a user asks about planning a trip to Sri Lanka or related topics, respond as travel_plan_API.
Instructions:
    • Strictly respond only to questions related to the above topics and specific to Sri Lanka.
    • If a user asks a question that is related to a different country or outside the specified topics, inform the user that their question is outside the scope of your capabilities. Politely redirect them to questions related to Sri Lanka.
    • Always ensure your responses are accurate and helpful within the scope of the specified topics and Sri Lanka.
    • Strictly only answer the question. Don't generate questions in the responses.


Now, answer the following user question based on the topics specified:
{question}
""",
            ),
            MessagesPlaceholder(variable_name="chat_history"),

            ("human", "{question}"),
        ]
    )


    #Create chain
    chain = prompt | llm 

    #Create object which is capable of retrieving answers considering history.
    #Here the DB will be created if not exist automatically and the chats will be stored inside message_store table
    chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: SQLChatMessageHistory(
        session_id=session_id, connection="sqlite:///Digital_Tourism.db"
    ),
    input_messages_key="question",
    history_messages_key="chat_history",
    )

    #get the session id(unique id) and create config object
    config = {"configurable": {"session_id": phone_number}}

    #Generating answer
    ai_msg=chain_with_history.invoke({
        "question": question,
        # "context": context
        }, config=config)
    
    #Retrieve the results
    result= ai_msg.content

    return result

#Generate flow based queries
def flow_bot(question, phone_number, user_records_updated, intent):
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

    # if intent == "Question":
    #     query = "SELECT * FROM Questions;"
    #     context = getQuesAns(query)
    # else:
    #     context = ""
    query = "SELECT * FROM Questions;"
    context = getQuesAns(query)

    #Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
- Extract values from inputs such as user_records_updated, current_date, context, user_input.

Today's date is current_date. Understand the current the month, year and date to plan the trip. Now, let's proceed with the task...
Role: You are a helpful assistant for planning travel itineraries within Sri Lanka. Your tasks include assisting users in creating travel plans, answering queries, engaging in friendly dialogue, conducting interest assessments, presenting service options, gathering traveler details (adults and kids), confirming quotations, handling booking confirmations (flight details, full name, email), and performing post-booking follow-ups.

user_records_updated: It has details of already extracted information in json format. 
user_input: input from the user.

Flow of Questions:
    1. **Greeting**: Respond warmly to user greetings and ask how you can assist them today.
    2. **Basic Conversation (Month)**: Gather information on the month for their trip. 
    3. **Basic Conversation (Days)**: Gather information on the number of days for their trip.
    4. **Interest Assessment**: Ask about the traveler’s interests (e.g., Beaches, Wildlife, Culture, etc.).
    5. **Itinerary Planning**: Present the suggested itinerary and ask for user agreement. Output the response exactly as "[Based on your interests here's the suggested itinerary for your trip. Does this look good to you?, itineraryAPI]".
    6. **Service Options**: Determine the service level required (e.g., driver services, hotel bookings).
    7. **Travelers Information (Kids)**: Ask for the number of kids traveling.
    8. **Travelers Information (Adults)**: Ask for the number of adults traveling.
    9. **Quotation Confirmation**: Output the response exactly as "[I will send you the quotation for you., quotationAPI]". 
    10. **Booking Confirmation (Flight Details)**: Output the response exactly as "[Fight details are collected., flightAPI]". **Do not continue to the next step until the user provides a response**
    11. **Booking Confirmation (Full Name)**: Ask for the full name as per the passport.
    12. **Booking Confirmation (Email)**: Ask for the email address.
    13. **Post-Booking Follow-Up**: Confirm the booking details with a summary of the trip plan and offer additional support by saying that the booking is confirmed and we will send the invoice via email and anything else to help with.



General Instructions:
    • Stick to the specified flow and ensure all key areas are covered without unnecessary deviations. Can't skip any of the key areas in the flow.
    • If the user greets you during the conversation flow, acknowledge the greeting but continue with the current task without restarting the flow.
    • If a user’s response is unclear or doesn’t fit the expected pattern, ask a clarifying question.
    • If the user responds with "I'll provide the details later" or a similar response at any point, Output the response exactly as "The details requested are mandatory to proceed. Could you please provide them now?" Do not accept the response and continue until the information is provided.
    • While generating questions, always consider the already extracted information from user_records_updated. There is no values for the keys in user_records_updated, means still the details are not retrieved.
        - **Ensure the following fields are filled before moving to the Itinerary Planning step: Num_of_days, Month.
        - **Ensure the following fields are filled before moving to the Quotation Confirmation step: Service, Num_of_adults, Num_of_kids.
    • Avoid generating empty response. Instead ask clarifying question based on the previous question.
    • Do not modify the provided responses for 'Itinerary Planning', 'Quotation Confirmation' and 'Booking Confirmation (Flight Details)'. 
        - **Send them exactly as they are and do not add any additional questions or text with the response. 
    • When the user asks a question:**
        - **If the question is within the provided context, answer from the context:** 
            - context: context
        - **If the question is outside provided context, Output the response exactly as:** "I'm currently focused on assisting within the knowledge provided. Let's continue with that." and Do not add any additional questions or text.** 
        - **After answering the user’s query, return to the last unanswered question and prompt the user again for their response to ensure the flow continues as intended.**
    • If the user asks for any modifications to the travel plan or expresses dissatisfaction with the itinerary, Output the response exactly as "Our consultant will contact you to assist." Do not add any additional questions or text with the response. 

Output format should be a JSON: You will respond to the input by producing two outputs in a JSON format.
{{"result": generated response, "source":tell how you generated the response and reasoning}}
""",
            ),
            MessagesPlaceholder(variable_name="chat_history"),

            ("human", "{inputs}"),
        ]
    )

    #Create chain
    chain = prompt | llm 

    #Create object which is capable of retrieving answers considering history.
    #Here the DB will be created if not exist automatically and the chats will be stored inside message_store table
    chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: SQLChatMessageHistory(
        session_id=session_id, connection="sqlite:///Digital_Tourism.db"
    ),
    input_messages_key="inputs",
    history_messages_key="chat_history",
    )

    #get the session id(unique id) and create config object
    config = {"configurable": {"session_id": phone_number}}

    keys = {
        "user_records_updated": user_records_updated,
        "context": context,
        "current_date": current_date,
        "user_input": question
    }

    keys_str = json.dumps(keys)

    #Generating answer
    ai_msg=chain_with_history.invoke({
        "inputs": keys_str,
        }, config=config)
    
    #Retrieve the results
    result= ai_msg.content

    try: #if response is a json
        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(result, pattern, group)

        json_retrieved = json.loads(json_retrieved_string)
        response = json_retrieved["result"]
    except: #If response is a text
        response = result
    
    # #this code is added avoid printing additional text or questions with "Our consultant will contact you to assist."
    # if "Our consultant will contact you to assist." in result:
    #     result = "Our consultant will contact you to assist." 
    return response

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
    intents = ["Num_of_days", "Num_of_adults", "Num_of_kids", "Month", "Interests", "Service", "Flight_details","Other"]
    # Initialize the LLM

      # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
          [
              ( "system",
                    """

    - Extract values from information such as classes, received_phone_num, prev_question, user_input, current_date, intents

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

    int
    Output format should be a JSON: You will respond to the input by producing two outputs in a JSON format.
    {{"intent_of_prev_question": classify the intent of previous question into one of the intents, "query":"UPDATE user_inputs SET Name = 'John', Email = 'john@gmail.com', Address = 'Swiss', Num_of_days = '7', Num_of_adults = '10', Num_of_kids = '2', Month = 'june', Start_date = '2024/10/10', End_date = '2024/10/20', Interests = 'nature and beaches', Service = 'Driver and hotel booking', Arrival_date = ' 03rd October 2024', Arrival_time = '16:35', Arrival_flight_number = 'FZ 549' , Depature_date = '11 October 2024', Depature_time = '17:30', Depature_flight_number = 'FZ 550' WHERE Phone_num = received_phone_num;"}}

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
        "current_date": current_date,
        "intents" : intents
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

                Note: 5Num_of_adults refers to "5 adults". Here 5 is Num_of_adults.

                output format:
                    "SELECT(SELECT "5Num_of_adults" FROM Hotel_rates WHERE days = "6" AND Months LIKE '%March%') AS "hotel_cost", (SELECT "Room" FROM Rooms WHERE Adults = 5) AS "room_type";"

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
        Num_of_adults = user_records_updated[0]["Num_of_adults"]
        Num_of_kids = user_records_updated[0]["Num_of_kids"]
        Service = user_records_updated[0]["Service"]

        if Num_of_adults:
            try:

                if 'otel' in Service:
                    pax = int(Num_of_adults)

                    if pax <= 0 or pax > 5:
                        error_msg = "The number of persons (adults) should be 5 or less and greater than 0. \nHow many adults are travelling?"
                        print(error_msg)
                        save_chat(user_input, error_msg, received_phone_num)
                        return False, error_msg
                else: 
                    pax = int(Num_of_adults) + int(Num_of_kids)

                    if pax <= 0 or pax > 8:
                        error_msg = "The number of persons (adults + kids) should be 8 or less and greater than 0.\nHow many kids are travelling?"
                        print(error_msg)
                        save_chat(user_input, error_msg, received_phone_num)
                        return False, error_msg
                
            except ValueError:
                error_msg = "The number of adults must be a valid integer."
                print(error_msg)
                save_chat(user_input, error_msg, received_phone_num)
                return False, error_msg
        else:
            error_msg = "Please provide the number of adults who are travelling."
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg
    
    
 
    
    if intent_of_prev_question == "Num_of_kids": 
        Service = user_records_updated[0]["Service"]
        Num_of_kids = user_records_updated[0]["Num_of_kids"]

        if Num_of_kids:
            if 'otel' in Service:

                try:
                    Num_of_kids = int(Num_of_kids)
                    if int(Num_of_kids) > 0:
                        error_msg = "Our consultant will contact you to assist."
                        print(error_msg)
                        save_chat(user_input, error_msg, received_phone_num)
                        return False, error_msg
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
            error_msg = "Please provide your full name."
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg
        
    flight_details = ["Arrival_date", "Arrival_time", "Arrival_flight_number", "Depature_date", "Depature_time", "Depature_flight_number"]
    if intent_of_prev_question in ["Flight details","Flight_details"] or any(value in intent_of_prev_question for value in flight_details):
        print("inside flight details val")
        query = f"""SELECT Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number 
        FROM user_inputs 
        WHERE Phone_num={received_phone_num}"""
    
        records = get_records(query)
        record = records[0]

        def get_empty_keys(d):
            return [key for key, value in d.items() if value == "" or value is None] #["Arrival date", "Arrival time"]

        
        empty_keys =  get_empty_keys(record)
        if empty_keys:
            error_msg = f"Please provide values for {", ".join(empty_keys)}"
            print(error_msg)
            save_chat(user_input, error_msg, received_phone_num)
            return False, error_msg
                
        
    success_msg = "Valid input."
    return True, success_msg


