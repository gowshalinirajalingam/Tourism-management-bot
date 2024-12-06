from agents import (
    UnansweredQuestionAgent,
    InputClassifierAgent,
    CommonQuestionHandlerAgent,
    GeneralConversationHandlerAgent,
    InformationRetrieverAgent,
    ValidationAgent,
    RouterAgent,
    MonthAgent,
    DayAgent,
    InterestAgent,
    ItineraryAgent,
    ServiceAgent,
    KidsAgent,
    AdultsAgent,
    QuotationAgent,
    FlightAgent,
    FullNameAgent,
    EmailAgent,
    BookingConfirmationAgent,
    CustomerCareAgent,
    HotelCostCalculatorAgent,
    HotelPriceListGeneratorAgent,
    QuotationDriverAgent,
    QuotationHotelAgent
)
from prompts import (
    input_classifier_template, 
    common_question_handler_template, 
    general_conversation_handler_template,
    information_retriever_template, 
    router_template,
    fetch_latest_unanswered_question,
    hotel_cost_calculation,
    hotel_price_list_generation,
    quotation_driver,
    quotation_hotel,
    chat_summarisation,
    paraphrase_questions
)

from state import GraphState
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from PIL import Image, ImageDraw
import io

from tools.ToolsLLM import parse_output_common
import json

def create_graph(model=None, temperature=0, max_tokens=0, server=None, key= None):

    #create graph object
    graph = StateGraph(GraphState)

    #Add nodes
    graph.add_node("UnansweredQuestion", 
    lambda state: UnansweredQuestionAgent(
        state=state,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        server=server,
        key=key
    ).invoke(
        prompt=fetch_latest_unanswered_question,
    )
    )
    
    graph.add_node("InputClassifier", 
        lambda state: InputClassifierAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=input_classifier_template
        )
        )
    graph.add_node("CommonQuestionHandler", 
        lambda state: CommonQuestionHandlerAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key

        ).invoke(
            prompt=common_question_handler_template,
        )
        )
    
    graph.add_node("GeneralConversationHandler", 
        lambda state: GeneralConversationHandlerAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key

        ).invoke(
            prompt=general_conversation_handler_template,
        )
        )
    
    graph.add_node("Validation", 
        lambda state: ValidationAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke()
        )
    

    graph.add_node("InformationRetriever", 
        lambda state: InformationRetrieverAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=information_retriever_template
        )
        )
    
    graph.add_node("Router", 
        lambda state: RouterAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=router_template
        )
        )
    
    graph.add_node("Month", 
        lambda state: MonthAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("Day", 
        lambda state: DayAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("Interest", 
        lambda state: InterestAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("Itinerary", 
        lambda state: ItineraryAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke()
        )
    
    graph.add_node("Service", 
        lambda state: ServiceAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("Kids", 
        lambda state: KidsAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("Adults", 
        lambda state: AdultsAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("Quotation", 
        lambda state: QuotationAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke()
        )
    
    graph.add_node("Flight", 
        lambda state: FlightAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke()
        )
    
    graph.add_node("FullName", 
        lambda state: FullNameAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("Email", 
        lambda state: EmailAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=paraphrase_questions
        )
        )
    
    graph.add_node("BookingConfirmation", 
        lambda state: BookingConfirmationAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt = chat_summarisation
        )
        )

    graph.add_node("CustomerCare", 
        lambda state: CustomerCareAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke()
        )
        
    
    graph.add_node("HotelCostCalculator", 
        lambda state: HotelCostCalculatorAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=hotel_cost_calculation,
        )
        )

    graph.add_node("HotelPriceListGenerator", 
        lambda state: HotelPriceListGeneratorAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=hotel_price_list_generation,
        )
        )
    
    graph.add_node("QuotationDriver", 
        lambda state: QuotationDriverAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=quotation_driver,
        )
        )
    
    graph.add_node("QuotationHotel", 
        lambda state: QuotationHotelAgent(
            state=state,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            server=server,
            key=key
        ).invoke(
            prompt=quotation_hotel,
        )
        )
    
    
    
    #conditional edge functions
    def decide_next_node_InputClassifier(state: GraphState):
        # intent = state["inputClassifier_response"][-1].content
        intent = state["inputClassifier_response"]

        next_node = "CommonQuestionHandler" if "Question" in intent else "InformationRetriever" if "Answer" in intent else "InformationRetriever"  if "Srilanka_trip" in intent else "CustomerCare" if "Change_request" in intent else "CommonQuestionHandler" if "Yes_question" in intent else "InformationRetriever" if "Yes_start_conv" in intent else "GeneralConversationHandler" if "No_start_conv" in intent else "InformationRetriever" if "No_question" in intent else "InformationRetriever" if "Yes_itinerary" in intent else "CustomerCare" if "No_itinerary" in intent else "InformationRetriever" if "No_general_conv" in intent else "GeneralConversationHandler" if "Yes_general_conv" in intent else "InformationRetriever" if "Yes_quotation" in intent else "CustomerCare" if "No_quotation" in intent else "CustomerCare" if "Yes_customer_care" in intent else "InformationRetriever" if "No_customer_care" in intent else "GeneralConversationHandler"
        return next_node
    
    def decide_next_node_Validation(state: GraphState):
        validation_status = state["Validation_response"]

        next_node = "Router" if validation_status else "__end__"
        return next_node

    def decide_next_node_Router(state):
        call_gen_q = state["router_response"]

        #Get only the next node
        # pattern = r'```json\n(.*?)\n```'
        # group = 1
        # json_retrieved_string = parse_output_common(call_gen_q, pattern, group)
        # print("json_retrieved_string:",json_retrieved_string)
        # json_retrieved = json.loads(json_retrieved_string)
        # next_node = json_retrieved['next_node']

        next_node = call_gen_q
        print("next node:",next_node)
        for value in {"Month", "Day", "Interest", "Itinerary", "Service", "Kids", "Adults", "Quotation", "Flight", "FullName", "Email", "BookingConfirmation"}:
            if value in next_node:
                next_node = value
                break
        else:
            next_node = "__end__"
        return next_node
    
    def decide_next_node_quotation(state: GraphState):
        Quotation_response = state["QuotationRouter_response"]
        
        next_node = "HotelCostCalculator" if "otel" in Quotation_response else "QuotationDriver"
        return next_node
    
    #Create Edges
    graph.add_edge(START, "UnansweredQuestion")
    graph.add_edge("UnansweredQuestion", "InputClassifier")
    graph.add_conditional_edges(
        "InputClassifier",
        decide_next_node_InputClassifier,
        {
        "CommonQuestionHandler": "CommonQuestionHandler",  #<class>:<node name>
        "InformationRetriever": "InformationRetriever",
        "CustomerCare": "CustomerCare",
        "GeneralConversationHandler": "GeneralConversationHandler", #it will connect to general conversaion handler
        }

        )

    graph.add_edge("InformationRetriever", "Validation")

    graph.add_conditional_edges(
        "Validation",
        decide_next_node_Validation,
            {
                "Router": "Router",  #<class>:<node name>
                "__end__": "__end__",
            }
        )
    
    graph.add_conditional_edges(
        "Router",
        decide_next_node_Router,
        {
            "Month": "Month", 
            "Day": "Day", 
            "Interest": "Interest", 
            "Itinerary": "Itinerary", 
            "Service": "Service", 
            "Kids": "Kids", 
            "Adults": "Adults", 
            "Quotation": "Quotation", 
            "Flight": "Flight", 
            "FullName": "FullName", 
            "Email": "Email", 
            "BookingConfirmation": "BookingConfirmation",
            "__end__": "__end__"

        }
        )
    
    graph.add_edge("Month", END)
    graph.add_edge("Day", END)
    graph.add_edge("Interest", END)
    graph.add_edge("Itinerary", END)
    graph.add_edge("Service", END)
    graph.add_edge("Kids", END)
    graph.add_edge("Adults", END)
    # graph.add_edge("Quotation", END)
    graph.add_edge("Flight", END)
    graph.add_edge("FullName", END)
    graph.add_edge("Email", END)
    graph.add_edge("BookingConfirmation", END)
    graph.add_edge("GeneralConversationHandler", END)
    graph.add_edge("CustomerCare", END)
    graph.add_edge("CommonQuestionHandler", END)

    graph.add_conditional_edges(
        "Quotation",
        decide_next_node_quotation,
        {
        "HotelCostCalculator": "HotelCostCalculator",  #<class>:<node name>
        "QuotationDriver": "QuotationDriver",
        }

    )

    graph.add_edge("HotelCostCalculator", "QuotationHotel")
    graph.add_edge("QuotationHotel", "HotelPriceListGenerator")
    graph.add_edge("HotelPriceListGenerator", END)
    graph.add_edge("QuotationDriver", END)


    





    return graph

def compile_workflow(graph, memory=False):
    
    if memory:
        from langgraph.checkpoint.memory import MemorySaver
        memory = MemorySaver()
        workflow = graph.compile(checkpointer=memory)
    else:
        workflow = graph.compile()
    return workflow

def save_workflow(workflow):
    image_data = workflow.get_graph().draw_mermaid_png()
    image = Image.open(io.BytesIO(image_data))
    image.save('graph.png')

