import dns.resolver
import re
from langchain_community.chat_message_histories import SQLChatMessageHistory

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
import os 
import json

def gen_context(vectordb, question):
    docs = vectordb.similarity_search(question, k=3)
    context = "\n".join([doc.page_content for doc in docs])
    doc_list = [doc.metadata for doc in docs]
    return context, doc_list

def parse_output_common(text, pattern, group):

    result = ''

    # Regular expression to match the SQL query

    # Find the SQL query using the regular expression
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    # Extract and print the SQL query
    if match:
        result = match.group(group)
        print(result)
    else:
        print("parse_output_common: No SQL match found.")
        result = text

    return result

def parse_output(output, received_phone_num):
    if "UPDATE" in output:
        # Extract the part between "SET" and "WHERE"
        set_line = output.split("SET", 1)[1].split("WHERE", 1)[0].strip()
        if set_line:
            # Extract the portion after "SET"
            keys = set_line.strip()[4:].strip()  # Remove "SET" and whitespace
            if not keys:  # If keys are empty
                return "SELECT 1 FROM user_inputs;"  # Return None if no keys to update
            
            return f"UPDATE user_inputs \nSET {set_line}\nWHERE Phone_num = {received_phone_num};"
    return "SELECT 1 FROM user_inputs;"

def save_chat(user_input, response, received_phone_num):
    chat_message_history = SQLChatMessageHistory(
    session_id=received_phone_num, connection="sqlite:///Digital_Tourism.db"
    )

    chat_message_history.add_user_message(user_input)
    chat_message_history.add_ai_message(response)

def save_to_pdf(df, pdf_path_hotel, hotel_cost, room_type, Num_of_adults):
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(pdf_path_hotel), exist_ok=True)
    
    doc = SimpleDocTemplate(pdf_path_hotel, pagesize=letter)
    
    # Convert DataFrame to a list of lists
    data = [df.columns.tolist()] + df.values.tolist()
    
    # Create a table
    table = Table(data)
    
    # Apply table style
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.deepskyblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.azure),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ])


    table.setStyle(style)
    
    title = Paragraph(f"""
                      <para align=center fontSize="16" spaceAfter="12">
                      <b>Accommodation Plan</b>
                      </para>
                      """)
    Meal = Paragraph(f"""
                     <para align=center>
                     <br/><br/>
                     BB - Bed & Breakfast, &nbsp;&nbsp;&nbsp; HB - Breakfast & Dinner, &nbsp;&nbsp;&nbsp; FB - Breakfast, Lunch & Dinner,<br/><br/>
                     AL - All Inclusive, &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; RO - Room Only, &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; DBL - Double Room.
                     </para>
                     """)
    # Calculate per-person cost
    if Num_of_adults == 0:
        Num_of_adults = 1
    per_person_cost = float(hotel_cost / Num_of_adults)

    room_type_para = Paragraph(f"""
                                     <para align=center fontSize="12" spaceAfter="12">
                                     <br/><br/>
                                     Room Count - ({room_type})
                                     </para>
                                     """)
    
    hotel_cost_paragraph = Paragraph(f"""
                                     <para align=center fontSize="12" spaceAfter="12">
                                     <br/><br/>
                                     Package Cost (Per-Person): &nbsp; US ${per_person_cost:.2f} <br/>
                                     Total Cost: US ${per_person_cost:.2f} x {Num_of_adults} Adults: &nbsp; US ${hotel_cost:.2f}

                                     </para>
                                     """)
    

    # Build the PDF
    elements = [title, table, Meal, room_type_para, hotel_cost_paragraph]

    doc.build(elements)
    print(f"PDF saved as {pdf_path_hotel}")

def has_mx_record(domain):
    try:
        # Query MX records
        records = dns.resolver.resolve(domain, 'MX')
        return len(records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False

def is_valid_email(email):

    try:
        local_part, domain = email.rsplit('@', 1)
        if not has_mx_record(domain):
            return False
        return True
    except ValueError:
        return False
    
def get_chat_history(history_records):
    extracted_data = []

    for item in history_records:
        message_data = json.loads(item['message'])
        message_type = message_data.get('type')
        message_content = message_data.get('data', {}).get('content')
        
        if message_type and message_content:
            extracted_data.append({
                'type': message_type,
                'content': message_content
            })
    return extracted_data