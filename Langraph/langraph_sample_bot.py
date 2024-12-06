"""
Built a sample langraph bot which takes user inuput and answer based on the toursm bot context.

Resources:
https://langchain-ai.github.io/langgraph/tutorials/introduction/

https://www.youtube.com/watch?v=R8KB-Zcynxc
https://github.com/menloparklab/LangGraphJourney/blob/main/LangGraphLearning.ipynb

https://www.youtube.com/watch?v=Al6Dkhuw3z0
https://github.com/hollaugo/langgraph-framework-tutorial/blob/main/Understanding_LangGraph_A_Podcast_production_workflow.ipynb
"""


from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


# Define grapgh object
graph_builder = StateGraph(State)


# DEFINE BOT
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

# Define LLM model
llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        max_tokens=50,
        temperature=0.5,
    )

# Define Agent function
def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]} #returning the message in state format


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()

# user_input = "What are the places to visit in silanka?"
# output = graph.invoke({"messages": ("user", user_input)})
# print("output:",output)

#SAVE GRAPGH
from IPython.display import Image, display
from PIL import Image, ImageDraw
import io


try:
    # display(Image(graph.get_graph().draw_mermaid_png()))
    image_data = graph.get_graph().draw_mermaid_png()
    image = Image.open(io.BytesIO(image_data))
    image.save('/home/senzmatepc27/Desktop/senzmate/Internal projects/Digital tourism/Github/Whatsapp-chatbot/graph.png')

except Exception:
    # This requires some extra dependencies and is optional
    pass




while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    for event in graph.stream({"messages": ("user", user_input)}):  # Transform the user input into State formate and pass into graph.stream. graph.stream will invoke the graph to generate the answer.
        for key, value in event.items():
            print(f"Output from node '{key}':")
            print("---")
            print(value)
    print("\n---\n")


