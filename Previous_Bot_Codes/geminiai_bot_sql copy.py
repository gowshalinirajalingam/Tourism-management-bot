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


# Load env variables from .env file
load_dotenv()
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

 # Define LLM model
llm = ChatGoogleGenerativeAI(
model="gemini-1.5-flash-latest",
max_tokens=250,
temperature=0.1,
)

#Get the context related to the question from vector db
def gen_context(vectordb, question):
    docs = vectordb.similarity_search(question, k=3)
    context = "\n".join([doc.page_content for doc in docs])
    doc_list = [doc.metadata for doc in docs]
    return context, doc_list

#Generate answer to the user queries
def qa_bot(question, phone_number):
    print("WELCOME TO Q&A SECTION")

    #Define paths
    persist_directory = '/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/Github/Whatsapp-chatbot/docs/chroma_predef_trips'

    #Load Vector DB
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

    #Define LLM model

    '''
    #Load and print chat history
    chat_history = SQLChatMessageHistory(
    session_id=phone_number, connection="sqlite:///Digital_Tourism.db"      
    )

    # # chat_history = read_chat_history(file_name)
    print("chat_history",chat_history)
    '''

    #Load context only relevant to the question
    context, doc_list = gen_context(vectordb, question)
    print("context:", context,"\n++++++++++++++")

    # Define LLM model


    #Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
You are an expert travel guide. 
context:{context}

Instructions:
- Please strictly note that if you couldn't find the answer from the context, send a response saying that I'm sorry, but it seems that the question is not relevant to the current context and don't buildup any answers.
- If the question is about quotation please tell the user that the quotation will be mailed.
""",
            ),
            MessagesPlaceholder(variable_name="history"),

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
    history_messages_key="history",
    )

    #get the session id(unique id) and create config object
    config = {"configurable": {"session_id": phone_number}}

    #Generating answer
    ai_msg=chain_with_history.invoke({
        "question": question,
        "context": context
        }, config=config)
    
    #Retrieve the results
    result= ai_msg.content

    #created this to store chat history in json file
#     
#     chat = f"""
# Human: {question}
# AI: {result}
#         """
    
#     write_user_history(file_name, chat, phone_number)

    return result

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

def generate_question_to_IR(user_input, received_phone_num, user_records):
    print("WELCOME TO GENERATE QUESTION TO IR SECTION")

    # Generate question for missing info
    user_records_json = user_records[0]
    print("user records:",user_records_json)

    # Define LLM model


    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             f"""
            You are a information retrieval ChatBot. 
            Your task is to generate questions to collect the missing values in the information. The information is in the form of json object. 
            The missing values in the information are filled with ''.
            
            The following are the description for the keys in the information collected.
            - 'Name refers to the name of the user.',
            - 'Email refers to the email of the user and the input should be in the default email format.',
            - 'num_of_days refers to how many days users plan to spend on their holiday or trip, and the input should be in numbers.',
            - 'num_of_adults refers to how many members plan to stay in a hotel or room, and the input should be in numbers.',
            - 'Service refers to the service customer wants either Driver service only or Driver and Hotel booking services.'


            Sample questions to generate:
            - 'Welcome to Sri Lanka Travel Assistant! How many days are you planning for your tour?' 
            - 'How many people will be staying?' 
            
             """),
            ("human", "{information}")
            ])



    # Create chain
    chain = prompt | llm

    # Generate the answer
    ai_msg = chain.invoke({
        "information": user_records_json
    })

    # Retrieve the results
    response = ai_msg.content

    save_chat(user_input, response, received_phone_num)
            
    return response

def retrieve_information(user_input,received_phone_num ):
    print("WELCOME TO INFORMATION RETRIEVAL SECTION")

    classes = ["Name", "Email", "Address", "Num_of_days", "Num_of_adults", "Month", "Start_date", "End_date", "Interests"]

    # Initialize the LLM

      # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
          [
              ( "system",
                  f"""
You are a information retrieval ChatBot. Retrieve the following information {', '.join(classes)} from the user_input.

Description for information are:
- 'Name refers to the name of the user.',
- 'Email refers to the email of the user and the input should be in the default email format.',
- 'Address refers to the address of the user.',
- 'num_of_days refers to how many days users plan to spend on their holiday or trip, and the input should be in numbers.',
- 'num_of_adults refers to how many members plan to stay in a hotel or room, and the input should be in numbers.',
- 'month refers to which month users plan to enjoy their trip or holiday, and the input should be the name of the month.',
- 'Start_date refers to the day the trip starts, and the input should be in the date format.',
- 'End_date refers to the day the trip ends, and the input should be in the date format.',
- 'Interests refers to the user's interests or preferences for the trip (e.g., beach, wildlife, nature, adventure).',
- 'Service refers to the service customer wants either Driver service only or Driver and Hotel booking services'


Current Question:
{user_input}

example for output:
UPDATE user_inputs
SET Name = "John", Email = "john@gmail.com", Address = "Swiss", Num_of_days = "7", Num_of_adults = "10", Month = "june", Start_date = "2024/10/10", End_date = "2024/10/20", Interests = "nature and beaches", Service = "Driver and hotel booking"
WHERE Phone_num = {received_phone_num};

Instructions:
- In the output only change the line starts with SET.
- The output should be strictly in given format and avoid unnecessary words.
- If the keys in line SET doesn't have values please remove those keys.
- If all of the keys doesn't have values just output SELECT 1 FROM user_inputs;
- If any service found in the user_input please classify it in to one of the two categories such as Driver, Driver and Hotel.

"""
						
              ),
              ("human", "{user_input}"),
          ]
      )

    # Create chain
    chain = prompt | llm

    # Generate the answer
    ai_msg = chain.invoke({
        "user_input": user_input
    })

    # Retrieve the results
    result = ai_msg.content

    retrieved_information = parse_output(result, received_phone_num)
    connection = sqlite3.connect('Digital_Tourism.db')
    cursor = connection.cursor()
    update_record_query = retrieved_information
    print("\n======================\n", update_record_query,"\n======================")
    cursor.execute(update_record_query)
    connection.commit()
    connection.close()

    return result

# Define the output parser
def parse_output(output, received_phone_num):
    if "UPDATE" in output:
        # Ensure only the SET line is included
        lines = output.splitlines()
        set_line = next((line for line in lines if line.strip().startswith("SET")), None)
        if set_line:
            return f"UPDATE user_inputs\n{set_line}\nWHERE Phone_num = {received_phone_num};"
    return "SELECT 1 FROM user_inputs;"

def save_chat(user_input, response, received_phone_num):
    chat_message_history = SQLChatMessageHistory(
    session_id=received_phone_num, connection="sqlite:///Digital_Tourism.db"
    )

    chat_message_history.add_user_message(user_input)
    chat_message_history.add_ai_message(response)