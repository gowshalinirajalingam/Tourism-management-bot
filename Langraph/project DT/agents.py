from state import GraphState
from tools.ToolsLLM import save_chat, get_chat, parse_output_common, parse_output, dict_to_meaningful_text, convert_to_conversation_format, is_valid_email, save_to_pdf
from tools.ToolsSQL import getQuesAns, get_chat_records, update_record, get_user_records, get_records, get_records_df

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from datetime import datetime
import json

from fuzzywuzzy import process

# from langchain_community.llms import OpenAI
# from langchain_community.chat_models import ChatOpenAI




class Agent:
    def __init__(self, state: GraphState, model=None, temperature=0, max_tokens=0, server=None, key=None):
        self.state = state
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.server = server 
        self.key = key
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.classes = ["Month","Num_of_days","Interests","Num_of_kids","Num_of_adults","Service","Arrival_date","Arrival_time","Arrival_flight_number","Depature_date","Depature_time","Depature_flight_number"]


    def get_llm(self):
        if self.server == 'gemini':
            # Define LLM model
            llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    api_key = self.key
                )     
        
    
        # if self.server == 'openai':
        #     # Define LLM model
        #     llm = ChatOpenAI(
        #         model_name=self.model,
        #         max_tokens=self.max_tokens,
        #         temperature=self.temperature,
        #         api_key = self.key


        #     )
        
        return llm

    def update_state(self, key, value):
        self.state = {**self.state, key: value}


class UnansweredQuestionAgent(Agent):
    def invoke(self, prompt=None):
        received_phone_num = self.state["received_phone_num"]


        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            previous_conversations = messages[-10:]
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        # print("previous_conversations(10):",previous_conversations)
        prompt = prompt.format(
            previous_conversations
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content
        print("latest unanswered question:",response)

        self.update_state("UnansweredQuestion_response", response)
        # self.update_state("bot_response", response)

        return self.state



class InputClassifierAgent(Agent):
    def invoke(self, prompt=None):
        input=self.state["input"]
        received_phone_num = self.state["received_phone_num"]
        
        # #Get previous 6 conversations
        # messages = get_chat(received_phone_num)
        # try:
        #     previous_conversations = messages[-6:]
        # except:
        #     previous_conversations = ""
        # previous_conversations = convert_to_conversation_format(previous_conversations)

        # print("previous_conversations input classifier:",previous_conversations)
        UnansweredQuestion=self.state["UnansweredQuestion_response"]

        prompt = prompt.format(
            input,
            UnansweredQuestion
        )

        
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content
        print("input class response",response)


        
        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['category']
        
        self.update_state("inputClassifier_response", response)

        return self.state
    
class CommonQuestionHandlerAgent(Agent):
    def invoke(self, prompt=None):
        input=self.state["input"]
        received_phone_num = self.state["received_phone_num"]


        query = "SELECT * FROM Questions;"
        context = getQuesAns(query)


        prompt = prompt.format(
            context,
            input
        )

        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)


        return self.state

class GeneralConversationHandlerAgent(Agent):
    def invoke(self, prompt=None):
        input=self.state["input"]
        received_phone_num = self.state["received_phone_num"]
        UnansweredQuestion=self.state["UnansweredQuestion_response"]


        #Get previous 6 conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-6:]
            previous_conversations = messages

        except:
            previous_conversations = ""
        print("previous_conversations:",previous_conversations)
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            input,
            previous_conversations,
            UnansweredQuestion
        )

        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string.strip())
        response = json_retrieved['response']

        save_chat(input, response, received_phone_num)


        self.update_state("bot_response", response)
        return self.state
    
class InformationRetrieverAgent(Agent):
    def invoke(self, prompt=None):
        input=self.state["input"]
        received_phone_num = self.state["received_phone_num"]
        UnansweredQuestion=self.state["UnansweredQuestion_response"]
        intents = ["Greeting","Name", "Num_of_days", "Num_of_adults", "Num_of_kids", "Month", "Interests", "Service", "Flight_details", "Other"]


        # #Get previous 6 conversations
        # messages = get_chat(received_phone_num)
        # try:
        #     previous_conversations = messages[-6:]
        # except:
        #     previous_conversations = ""
        # previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            self.current_date,
            ','.join(self.classes),
            UnansweredQuestion,
            input,
            received_phone_num,
            intents
        )

        
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        #TODO TOOLS
        #update database
        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        print("json_retrieved_string:",json_retrieved_string)
        json_retrieved = json.loads(json_retrieved_string)
        retrieved_information = json_retrieved['query']
        retrieved_information = parse_output(retrieved_information, received_phone_num)
        intent_of_prev_question = json_retrieved['intent_of_prev_question'] 
        update_record(retrieved_information)

        #update days if start_date and end_date available
        query = f"""SELECT Start_date, End_date
        FROM user_inputs 
        WHERE Phone_num={received_phone_num}"""
    
        records = get_records(query)
        start_date_str = records[0]["Start_date"]
        end_date_str = records[0]["End_date"]
        if start_date_str and end_date_str:
            print("adfgd:")
            try:
                if start_date <= end_date:
                    print("start val")
                    date_format="%Y/%m/%d"
                    start_date = datetime.strptime(start_date_str, date_format)
                    end_date = datetime.strptime(end_date_str, date_format)
                    num_of_days = (end_date - start_date).days + 1  # Adding 1 to include both dates
                    print("num_of_days",num_of_days)
                    query = f"""
                    UPDATE user_inputs
                    SET Num_of_days = {num_of_days}
                    WHERE Phone_num = {received_phone_num};
                    """
                    update_record(query)
                else:
                    pass
            except:
                pass #if the dates are invalid or start date > end date or any other exception occurs just pass. these will be validated in validation agent.


        self.update_state("informationRetriever_response", response)
        return self.state
    
class ValidationAgent(Agent):
    def invoke(self, prompt=None):
        received_phone_num = self.state["received_phone_num"]
        user_input=self.state["input"]
        error_msg=""
        validating_col=""
        informationRetriever_response = self.state["informationRetriever_response"]

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(informationRetriever_response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)
        intent_of_prev_question = json_retrieved['intent_of_prev_question'] 
         

        cols = "Month, Num_of_days, Start_date, End_date, Interests, Itinerary_status, Service, Num_of_kids, Num_of_adults, Quotation_status, Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number, Name, Email, Hotel_kids_status"
        collected_info = get_user_records(received_phone_num, cols )  # retrieve records after updating the extracted values
        print("collected_info",collected_info)

        for validating_col in cols.split(", "):
            if validating_col == "Start_date" or validating_col == "End_date":
                start_date_str = collected_info[0]["Start_date"]
                end_date_str = collected_info[0]["End_date"]
                        
                if start_date_str and end_date_str:
                    try:
                        date_format="%Y/%m/%d"
                        start_date = datetime.strptime(start_date_str, date_format)
                        end_date = datetime.strptime(end_date_str, date_format)
                    except:
                        error_msg = "The dates you provided are invalid. Can you provide the dates again?"
                        break
                    
                    if start_date > end_date:
                        error_msg = "The trip starting date must be later than the ending date. Can you provide the dates again?"
                        break
        

            if validating_col == "Month":
                month = collected_info[0]["Month"]

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
                        break

                    else:  # The database hase only values for temp_months. So the user input should be inside that.
                        #VALIDATE WITH THE DATA AVAILABLE IN DB
                        temp_months = [ "January", "February", "March", "April", "September", "October", "November", "December"]
                        
                        # Find the closest match from valid_months
                        closest_match, score = process.extractOne(month, temp_months)
                        
                        # Define a threshold score for considering a match valid
                        threshold = 80  # You can adjust this threshold
                        
                        if score < threshold:
                            # error_msg = "Can you provide months from Jan-Apr or Sep-Dec? We are working on the month you provided?"
                            error_msg = "We don't have data for the month you provided. Do you want to contact an agent? "
                            break
                        
                        #VALIDATE WHETHER THE MONTH MATCHES WITH START DATE
                        # Check the month matches with the start date because sometimes if the user changes the month, the month may be different from start date. if start date are not empty, ask start date again 
                        start_date_str = collected_info[0]["Start_date"]
                                
                        if start_date_str:

                            try:
                                date_format="%Y/%m/%d"
                                start_date = datetime.strptime(start_date_str, date_format)
                                start_month = start_date.strftime("%B")  # e.g., "November"

                                if start_month.lower() != closest_match.lower():
                                    error_msg = "The provided month is mis-matching with the dates provided previously. Please provide the start date and end date again?"
                                    break

                            except Exception as e:
                                error_msg = "The start date you provided is invalid. Can you provide the date again?"
                                break
                    
                elif intent_of_prev_question == "Month":
                        error_msg = "Can you please provide the month that you are planning to travel?"
                        break
                

            
            # Validate num_of_days
            if validating_col == "Num_of_days":
                days = collected_info[0]["Num_of_days"]

                if days:
                    try:
                        days = int(days)
                        if days <= 4 or days > 14:
                            error_msg = "The number of travelling days should be in between 5 to 14. Can you please provide the days again?"
                            break

                    except ValueError:
                        error_msg = "The number of travelling days must be a valid integer. Can you please provide the month again?"
                        break

                elif intent_of_prev_question == "Num_of_days":
                    error_msg = "Can you please provide the number of days that you are travelling?"
                    break
            
            
            
            # Validate num_of_adults
            if validating_col == "Num_of_adults":
                Num_of_adults = collected_info[0]["Num_of_adults"]
                Service = collected_info[0]["Service"]

                if Num_of_adults:
                    try:
                        if Service:
                            if 'otel' in Service: #driver and hotel service
                                pax = int(Num_of_adults)


                                if pax <= 0 or pax > 5:
                                    error_msg = "The number of persons (adults) should be 5 or less and greater than 0. \nHow many adults are travelling?"
                                    break
                            else:  #Driver service
                                if Num_of_kids: # if kids has value only sum the values below. else kids may be empty value and throw error
                                    pax = int(Num_of_adults) + int(Num_of_kids)

                                    if pax <= 0 or pax > 8:
                                        error_msg = "The number of persons (adults + kids) should be 8 or less and greater than 0.\nHow many kids are travelling?"
                                        break
                                # else:
                                #     error_msg = "How many kids are travelling?"
                                #     #if we don't return here it will empty the adults count in database and again it will ask for adults count.
                                #     save_chat(user_input, error_msg, received_phone_num)
                                #     self.update_state("bot_response", error_msg)
                                #     self.update_state("Validation_response", False)
                                #     return self.state
                        
                    except Exception as e:
                        error_msg = "The number of adults must be a valid integer."
                        break

                elif intent_of_prev_question == "Num_of_adults":
                    error_msg = "Can you please provide the number of adults who are travelling?"
                    break
        
            
            # Validate num_of_kids

            if validating_col == "Num_of_kids":
                
                Num_of_kids = collected_info[0]["Num_of_kids"]
                Service = collected_info[0]["Service"]
                Hotel_kids_status = collected_info[0]["Hotel_kids_status"]
                

                if Num_of_kids:
                    if 'otel' in Service and Hotel_kids_status == "False":

                        try:
                            Num_of_kids = int(Num_of_kids)
                            if int(Num_of_kids) > 0:
                                error_msg = "Providing hotel services for kids require consultantant support. Our consultant will contact you to assist."
                                #update DB
                                query = f"""
                                UPDATE user_inputs
                                SET Hotel_kids_status = "True"
                                WHERE Phone_num = {received_phone_num};
                                """
                                update_record(query)

                                #if we don't return here it will empty the kids count in database at the end of this function and again the router node will predict the next node as Kids.
                                save_chat(user_input, error_msg, received_phone_num)
                                self.update_state("bot_response", error_msg)
                                self.update_state("Validation_response", False)
                                return self.state

                        except ValueError:
                            error_msg = "The number of kids must be a valid integer. Can you please provide the kids count again?"
                            break

                elif intent_of_prev_question == "Num_of_kids":
                    error_msg = "Can you please provide the number of kids that you are travelling?"
                    break
            
            # Validate email
            if validating_col == "Email":
                email = collected_info[0]["Email"]

                    
                if email:
                    if not is_valid_email(email):
                        error_msg = "The email is invalid. Can you please provide a valid email address?"
                        break
                            
                elif intent_of_prev_question == "Email":
                    error_msg = "Can you please provide your email address?"
                    break
                
            # Validate name
            if validating_col == "Name":
                name = collected_info[0]["Name"]

                # If the user didn't provide the name it will send a error message. We can add validation part in future.
                if name:
                    pass
                elif intent_of_prev_question == "Name":
                    error_msg = "Can you please provide your full name?"
                    break

            # Validate flight details
            flight_details = ["Arrival_date", "Arrival_time", "Arrival_flight_number", "Depature_date", "Depature_time", "Depature_flight_number"]
            if validating_col in flight_details:
                if intent_of_prev_question.lower() in ["flight details","flight_details","arrival_depature_details"] or any(value in intent_of_prev_question for value in flight_details): 
                    print("inside flight details val")
                    # query = f"""SELECT Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number 
                    # FROM user_inputs 
                    # WHERE Phone_num={received_phone_num}"""
                
                    # records = get_records(query)
                    # record = records[0]

                    cols = "Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number"
                    collected_info_flight = get_user_records(received_phone_num, cols )  # retrieve records after updating the extracted values

                    def get_empty_keys(d):
                        return [key for key, value in d.items() if value == "" or value is None] #["Arrival date", "Arrival time"]

                    
                    empty_keys =  get_empty_keys(collected_info_flight[0])
                    if empty_keys:
                        error_msg = f"Can you please provide values for {", ".join(empty_keys)}?"
                        
                        # have to exit here. because when Arrival_date comes as validating_col it will check for other empty columns(eg.Depature_time, Depature_flight_number ) and emptying Arrival_date at the end of the function. So that Arrival date validation will come again and asks for Arrival date always.
                        save_chat(user_input, error_msg, received_phone_num)
                        self.update_state("bot_response", error_msg)
                        self.update_state("Validation_response", False)
                        return self.state
                
            
        if error_msg:

            #update DB
            query = f"""
            UPDATE user_inputs
            SET {validating_col} = ""
            WHERE Phone_num = {received_phone_num};
            """
            update_record(query)

            if validating_col == "Num_of_days" or validating_col == "Month": # in this case empty start_date, end_date as well. else the days will be calculated again and again from start_date and end_date and it will be a loop.
                #update DB
                query = f"""
                UPDATE user_inputs
                SET Start_date = "", End_date = ""
                WHERE Phone_num = {received_phone_num};
                """
                update_record(query)
            
            if validating_col == "Start_date" or validating_col == "End_date": # in this case empty start_date, end_date as well. else the days will be calculated again and again from start_date and end_date and it will be a loop.
                #update DB
                query = f"""
                UPDATE user_inputs
                SET Num_of_days = "", Month = ""
                WHERE Phone_num = {received_phone_num};
                """
                update_record(query)
            
            
            save_chat(user_input, error_msg, received_phone_num)
            self.update_state("bot_response", error_msg)
            self.update_state("Validation_response", False)
        else:
            self.update_state("Validation_response", True)
        return self.state
    
    
class RouterAgent(Agent):
    def invoke(self, prompt=None):
        cols = "Month, Num_of_days, Interests, Itinerary_status, Service, Num_of_kids, Num_of_adults, Quotation_status, Arrival_date, Arrival_time, Arrival_flight_number, Depature_date, Depature_time, Depature_flight_number, Name, Email, Hotel_kids_status"
        received_phone_num = self.state["received_phone_num"]
        collected_info = get_user_records(received_phone_num, cols )  # retrieve records after updating the extracted values

        collected_info_meaningful = dict_to_meaningful_text(collected_info)
        # collected_info = ",".join(collected_info)
        print("collected info:",collected_info_meaningful)

        #validation
        #TODO
        #call next node based on data availability
        replace_dict = {"Num_of_days": "Day","Interests":"Interest","Itinerary_status":"Itinerary","Num_of_kids":"Kids","Num_of_adults":"Adults","Quotation_status":"Quotation","Name":"FullName"}  # Dictionary for replacements

        missing_words_itinerary = [replace_dict.get(word, word) for word in ['Month', 'Num_of_days', 'Interests','Itinerary_status'] if word not in collected_info_meaningful[0]]
        missing_words_quotation = [replace_dict.get(word, word) for word in ['Service','Num_of_kids','Num_of_adults','Quotation_status'] if word not in collected_info_meaningful[0]]
        missing_words_flight = [replace_dict.get(word, word) for word in ['Arrival_date','Arrival_time','Arrival_flight_number','Depature_date','Depature_time','Depature_flight_number'] if word not in collected_info_meaningful[0]]
        missing_words_booking = [replace_dict.get(word, word) for word in ['Name','Email'] if word not in collected_info_meaningful[0]]

        if missing_words_itinerary:
            next_node = missing_words_itinerary[0]
        elif missing_words_quotation:
            next_node = missing_words_quotation[0]
        elif missing_words_flight:
            next_node = "Flight"
        elif missing_words_booking:
            next_node = missing_words_booking[0]
        else:
            next_node = "BookingConfirmation"


        Hotel_kids_status = collected_info[0]["Hotel_kids_status"]
        if next_node == 'Kids' and Hotel_kids_status=="True":
            #Added this code here to solve the problem if service is hotel and kids count is there, when it comes after connecting to the agent, it again asks how many kids are travelling. We should ask how many adults are travelling.
            response = 'Adults'
        else:
            response = next_node

        self.update_state("router_response", response)
        return self.state
    

class MonthAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        
        question = "Great! To start planning, what month are you looking to travel to Sri Lanka?"
        
        #PARAPHRASING THE QUESTION
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    

class DayAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        
        question = "How many days are you planning to spend in Sri Lanka?"
        
        #PARAPHRASING THE QUESTION
         #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']


        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state

class InterestAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        
        question = "Great! Tell me a little about your interests. Are you interested in beaches, wildlife, culture, all of them, or something else?"
        
        #PARAPHRASING THE QUESTION
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    
class ItineraryAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        
        response = "itineraryAPI"
        
        #update DB
        query = f"""
UPDATE user_inputs
SET Itinerary_status = "True"
WHERE Phone_num = {received_phone_num};
	"""
        update_record(query)

        save_chat(input, "Based on your interests here's the suggested itinerary for your trip. Does this look good to you?", received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    
class ServiceAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        question = "What kind of service level are you looking for? Would you like driver service only, or driver service and hotel bookings?"
        
        #PARAPHRASING THE QUESTION
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    
class KidsAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        question = "Could you let me know the number of kids if any are joining?"
        
        #PARAPHRASING THE QUESTION
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    
class AdultsAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        question = "How many adults will be traveling?"
        
        #PARAPHRASING THE QUESTION
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    
class QuotationAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]

        columns = "Num_of_days, Num_of_adults, Num_of_kids, Service, Month"
        records = get_user_records(received_phone_num, columns)
        Service = records[0]["Service"]
        
        #update DB
        query = f"""
UPDATE user_inputs
SET Quotation_status = "True"
WHERE Phone_num = {received_phone_num};
	"""
        update_record(query)


        save_chat(input, "Based on the service, Num_of_adults and Num_of_kids, we sent the quotation for you. Are you satisfied with the quotation?", received_phone_num)
        self.update_state("QuotationRouter_response", Service)

        return self.state
    
    
class FlightAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        response = "flightAPI"
        
        save_chat(input, "We are going to collect flight details.", received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    
class FullNameAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        question = "Great! What is your full name as per the passport?"
        
        #PARAPHRASING THE QUESTION
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state
    
class EmailAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        question = "Nice! What is your email address?"

        #PARAPHRASING THE QUESTION
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations,
            question
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        pattern = r'```json\n(.*?)\n```'
        group = 1
        json_retrieved_string = parse_output_common(response, pattern, group)
        json_retrieved = json.loads(json_retrieved_string)

        response = json_retrieved['paraphrased_question']
        
        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state

class BookingConfirmationAgent(Agent):
    def invoke(self, prompt=None):
        input = self.state["input"].strip()
        received_phone_num = self.state["received_phone_num"]
        response = "Your booking is confirmed and we will send the invoice via email."
        
        # RECIEVE THE CHAT SUMMARY
        #Get previous conversations
        messages = get_chat(received_phone_num)
        try:
            # previous_conversations = messages[-10:]
            previous_conversations = messages
        except:
            previous_conversations = ""
        previous_conversations = convert_to_conversation_format(previous_conversations)

        prompt = prompt.format(
            previous_conversations
        )
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        summary_response = ai_msg.content
        print("chat summary:",summary_response)

        response = response + "\n\n" + summary_response

        save_chat(input, response, received_phone_num)
        self.update_state("bot_response", response)
        return self.state

class CustomerCareAgent(Agent):
    def invoke(self, prompt=None):
    
        response = "Our consultant will contact you to assist"
        
        self.update_state("bot_response", response)

        return self.state



class QuotationDriverAgent(Agent):
    def invoke(self, prompt=None):
        received_phone_num = self.state["received_phone_num"]

        columns = "Num_of_days, Num_of_adults, Num_of_kids, Service, Month"
        records = get_user_records(received_phone_num, columns)

        Num_of_days =  int(records[0]["Num_of_days"])
        Num_of_adults =  int(records[0]["Num_of_adults"])
        Num_of_kids =  int(records[0]["Num_of_kids"])
        Month = records[0]["Month"]
        pax = Num_of_kids + Num_of_adults

        prompt = prompt.format(
            Num_of_days,
            pax,
            Month
        )
        
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        group = 0
        pattern = r'\bSELECT\b.*?;'
        response = parse_output_common(response, pattern, group)

        records = get_records(response)  #[{'driver_cost': 535, 'km': 850, 'extra_rate': 110, 'vechile': 'FLATROOF VAN'}]  
        print(records)
        cost = int(records[0]["driver_cost"])
        km = int(records[0]["km"])
        extra_rate = int(records[0]["extra_rate"])
        vehicle = records[0]["vehicle"]
        per_person_cost = int(cost/int(pax))
        



        response = f"""
It’s *{cost}USD* for {Num_of_days} days for {Num_of_adults} adults and {Num_of_kids} kids. 
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

        response = "*English Speaking Tourist Driver*\n\n"+ response

        self.update_state("bot_response", response)

        return self.state
    

class QuotationHotelAgent(Agent):
    def invoke(self, prompt=None):
        received_phone_num = self.state["received_phone_num"]

        columns = "Num_of_days, Num_of_adults, Num_of_kids, Service, Month"
        records = get_user_records(received_phone_num, columns)

        Num_of_days =  int(records[0]["Num_of_days"])
        Num_of_adults =  int(records[0]["Num_of_adults"])
        Num_of_kids =  int(records[0]["Num_of_kids"])
        Month = records[0]["Month"]
        pax = Num_of_kids + Num_of_adults

        prompt = prompt.format(
            Num_of_days,
            pax,
            Month
        )
        
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        group = 0
        pattern = r'\bSELECT\b.*?;'
        response = parse_output_common(response, pattern, group)

        records = get_records(response)  #[{'km': 850, 'extra_rate': 110, 'vechile': 'FLATROOF VAN'}]  
        print(records)

        HotelCostCalculator_response = self.state["HotelCostCalculator_response"]
        hotel_cost = int(HotelCostCalculator_response[0]["hotel_cost"])

        cost = hotel_cost
        km = int(records[0]["km"])
        extra_rate = int(records[0]["extra_rate"])
        vehicle = records[0]["vehicle"]
        per_person_cost = int(cost/int(pax))
        



        response = f"""
It’s *{cost}USD* for {Num_of_days} days for {Num_of_adults} adults and {Num_of_kids} kids. 
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

        if int(Num_of_kids) > 0:
                response = "*Hotels + English Speaking Tourist Driver*\n\n"+ response +"\n\n"+ "Please find the hotel details and price. \nThere will a slight change in the provided details as kids are included."
        else:
                response = "*Hotels + English Speaking Tourist Driver*\n\n"+ response +"\n\n"+ "Please find the hotel details and price."
        
        self.update_state("bot_response", response)

        return self.state
    


    
class HotelCostCalculatorAgent(Agent):
    def invoke(self, prompt=None):
        received_phone_num = self.state["received_phone_num"]

        columns = "Num_of_days, Num_of_adults, Num_of_kids, Service, Month"
        records = get_user_records(received_phone_num, columns)

        Num_of_days =  int(records[0]["Num_of_days"])
        Num_of_adults = int(records[0]["Num_of_adults"])
        Num_of_kids =  int(records[0]["Num_of_kids"])
        Month = records[0]["Month"]

        prompt = prompt.format(
            Num_of_days,
            Num_of_adults,
            Num_of_kids,
            Month
        )
        
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        group = 0
        pattern = r'\bSELECT\b.*?;'
        response = parse_output_common(response, pattern, group)

        records = get_records(response)  #[{'hotel_cost': 535, 'km': 850, 'extra_rate': 110, 'vechile': 'FLATROOF VAN'}]  
        print(records)

        self.update_state("HotelCostCalculator_response", records)

        return self.state
    

class HotelPriceListGeneratorAgent(Agent):
    def invoke(self, prompt=None):
        received_phone_num = self.state["received_phone_num"]
        pdf_path_hotel = "Hotel_rates_output_pdf/"+received_phone_num+".pdf"
        # response = "quotationAPI"

        HotelCostCalculator_response = self.state["HotelCostCalculator_response"]
        room_type = HotelCostCalculator_response[0]["room_type"]
        hotel_cost = int(HotelCostCalculator_response[0]["hotel_cost"])

        columns = "Num_of_days, Num_of_adults, Num_of_kids, Service, Month"
        records = get_user_records(received_phone_num, columns)

        Num_of_days =  int(records[0]["Num_of_days"])
        Month = records[0]["Month"]
        Num_of_adults = int(records[0]["Num_of_adults"])


        prompt = prompt.format(
            Num_of_days,
            Month
        )
        
        llm = self.get_llm()
        ai_msg = llm.invoke(prompt)
        response = ai_msg.content

        group = 0
        pattern = r'\bSELECT\b.*?;'
        response = parse_output_common(response, pattern, group)
        df = get_records_df(response)
        save_to_pdf(df, pdf_path_hotel, hotel_cost, room_type, Num_of_adults)

        self.update_state("HotelPriceListGenerator_response", pdf_path_hotel) #this will help to send the hotel list pdf in run.py file
        # self.update_state("bot_response", response) #this will help to send the hotel list pdf in run.py file

        return self.state
    



