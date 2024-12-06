from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
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
You are a helpful assistant for planning travel itineraries. 
Your main tasks are to assist users in creating travel plans, answer basic conversational greetings, and engage in friendly dialogue. 


Instructions:
- For the trip planning only details needed are the month and number of days planned for trip.
- Only answer from context based on the season and number of days planned for trip.
- If answer not found from the context please say that I'm sorry, but it seems that the question is not relevant to the current context.
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
    print(result)

    #created this to store chat history in json file
#     
#     chat = f"""
# Human: {question}
# AI: {result}
#         """
    
#     write_user_history(file_name, chat, phone_number)

    return result

# qa_bot("How to book train ticket?","23425325")
qa_bot("Suggest a travel plan in srilanka","23425325")