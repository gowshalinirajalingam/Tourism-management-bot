"""
This code explains creating a whatsapp chatbot using Google Gemini.ai
Here chat history is stored in a json file and loaded to memory.
"""

'''
from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory

import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from langchain_community.vectorstores import Chroma

def qa_bot(question):
    load_dotenv()

    GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
    print("GOOGLE_API_KEY_Geminiai_bot:",GOOGLE_API_KEY)
    persist_directory = '/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/Digital tourism whatsapp bot/docs/chroma_predef_trips'

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        max_tokens=250,
        temperature=0.5,
    )

    template = """
    You are a useful. friendly tourism chatbot. 
    If someone greets you, you greet them back..
    Use the following pieces of context to answer the question at the end. 
    Please consider chat_history while answering.
    If the answer is not found from the context, say I'm not able to answer your question. 
    If the answer is not found from the context, Don't try to make up an answer. 
    Use three sentences maximum. Keep the answer as concise as possible.\n
    \n
    This is the context:{context},
    this is chat_history:{chat_history}
    Question: {question}
    Helpful Answer:"""

    QA_CHAIN_PROMPT = PromptTemplate(input_variables=["context", "chat_history", "question"], template=template)

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=vectordb.as_retriever(),
        return_source_documents=True,
        verbose=True,
        chain_type_kwargs={
            "verbose": False,
            "prompt": QA_CHAIN_PROMPT,
            "memory": ConversationBufferMemory(
                memory_key="chat_history",
                input_key="question"),
        }
    )

    result = qa_chain.invoke({"query": question})
    return result["result"]
'''

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from langchain.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferWindowMemory
import json 


load_dotenv()
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

# Initialize memory once and keep it persistent
# memory = ConversationBufferWindowMemory(k=6)

def gen_context(vectordb, question):
    docs = vectordb.similarity_search(question, k=3)
    context = "\n".join([doc.page_content for doc in docs])
    doc_list = [doc.metadata for doc in docs]
    return context, doc_list

def qa_bot(question, phone_number):
    persist_directory = '/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/Digital tourism whatsapp bot/docs/chroma_predef_trips'
    file_name = "/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/Github/Whatsapp-chatbot/chat_history/"+phone_number+".json"

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        max_tokens=250,
        temperature=0.5,
    )

    # chat_history = memory.load_memory_variables({})['history']
    chat_history = read_chat_history(file_name)
    print("chat_history",chat_history)

    context, doc_list = gen_context(vectordb, question)


    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
You are an expert travel guide. The following is a transcript of a conversation with a user asking about various travel-related topics. Please use the context to answer the user's latest question accurately.

Conversation History:
- User: "I’m interested in visiting historical sites in SriLanka. What do you recommend?"
- Assistant: "You should visit the Sigiriya, the Dalathamaligava, and the Dambulla golden temple. Also, consider the Polannaruwa vigara."

Current Question:
"Are there any good local restaurants near the Sigiriya?"

Instructions:
- Incorporate relevant information from the chat_history and context to provide a response.
- If the question is out of context please say I understand your question, but it’s outside the scope of what I can assist with. 

context: {context}
chat_history: {chat_history}
question: {question}
                """,
            ),
            ("human", f"{question}"),
        ]
    )


    chain = prompt | llm 

    ai_msg = chain.invoke({
        "context": context,
        "chat_history": chat_history,
        "question": question
    })

    # memory.save_context({"input": question}, {"output": ai_msg.content})

    result = ai_msg.content

    chat = f"""
Human: {question}
AI: {result}
        """
    

    write_user_history(file_name, chat, phone_number)
    return result
    
def write_user_history(file_name, chat, phone_number):

    if not os.path.exists(file_name):
        user_details = {
            "phone_number":"",
            "session_id":"",
            "chat_start_time":"",
            "chat_end_time":"",
            "chat_history":chat
            }
        with open(file_name, 'w') as file:
            json.dump(user_details, file, indent=4)
        return f"New user {phone_number} file is created"
    else:
        existing_content = read_user_history(file_name)
        chat_history = existing_content['chat_history']
        chat_history = f"{chat_history}{chat}"  #Adding new chat to the old one
        existing_content['chat_history'] = chat_history

        with open(file_name, 'w') as file:
            json.dump(existing_content, file, indent=4)
        return f"User {phone_number} file is updated"

def read_user_history(file_name):
    with open(file_name, 'r') as file:
        existing_content = json.load(file)

    return existing_content

def read_chat_history(file_name):
    if not os.path.exists(file_name):
        chat_history = ""
    else:
        with open(file_name, 'r') as file:
            existing_content = json.load(file)
            chat_history = existing_content['chat_history']

    return chat_history

