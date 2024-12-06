from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv


import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from langchain_community.vectorstores import Chroma



load_dotenv()

GOOGLE_API_KEY=os.environ["GOOGLE_API_KEY"]
persist_directory = '/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/Github/Whatsapp-chatbot/docs/chroma_predef_trips/'

def get_pdf():
    # Load PDF
    loaders = [
        # Duplicate documents on purpose - messy data
        PyPDFLoader("whatsapp_bot_gemini/pdf_chat/lecture_01.pdf")
        
    ]
    docs = []
    for loader in loaders:
        docs.extend(loader.load())


    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1500,
        chunk_overlap = 150
    )
    chunks = text_splitter.split_documents(docs)
    return chunks


def read_docx():
    directory_path = '/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/drive-download-20240708T053302Z-001/Predefined Trip Plans'
    docs = []
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            print(os.path.join(path, name))
            file_path = os.path.join(path, name)
            loader = Docx2txtLoader(file_path)
            docs.extend(loader.load())


    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1500,
        chunk_overlap = 150
    )
    chunks = text_splitter.split_documents(docs)
    return chunks

chunks = read_docx()
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

if not os.path.exists(persist_directory):
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    vectordb.persist()
