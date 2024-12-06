from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

# Define the state object for the agent graph
class GraphState(TypedDict):
    input: str
    received_phone_num:str
    UnansweredQuestion_response:str
    Validation_response:bool
    QuotationRouter_response:str
    HotelCostCalculator_response:str
    HotelPriceListGenerator_response:str
    inputClassifier_response: str
    informationRetriever_response: str
    router_response: str
    # handle_month_response: Annotated[list, add_messages]
    # handle_day_response: Annotated[list, add_messages]
    # history: Annotated[list, add_messages]
    bot_response:str

