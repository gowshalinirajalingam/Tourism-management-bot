import sqlite3

# Create user_inputs table
connection = sqlite3.connect('Digital_Tourism.db')
cursor = connection.cursor()
create_table_query = '''
CREATE TABLE "user_inputs" (
	"Phone_num"	TEXT,
	"Name"	TEXT,
	"Email"	TEXT NOT NULL,
	"Address"	TEXT,
	"Num_of_days"	TEXT,
	"Num_of_adults"	TEXT,
	"Num_of_kids"	TEXT,
	"Month"	TEXT,
	"Start_date"	TEXT,
	"End_date"	TEXT,
	"Interests"	TEXT,
	"Service"	TEXT,
	"Last_message_retrieve_time"	TEXT,
	"Agent_mode"	TEXT,
	"Arrival_date"	TEXT,
	"Arrival_time"	TEXT,
	"Arrival_flight_number"	TEXT,
	"Depature_date"	TEXT,
	"Depature_time"	TEXT,
	"Depature_flight_number"	TEXT,
	"Itinerary_status"	TEXT,
	"Quotation_status"	TEXT,
    "Hotel_kids_status" TEXT,
	PRIMARY KEY("Phone_num")
);
'''

cursor.execute(create_table_query)
connection.commit()
connection.close()

print("user_inputs Table created successfully.")



# Create message_store table. because the table which is been created automatically by langchain will not contain timestamp column
connection = sqlite3.connect('Digital_Tourism.db')
cursor = connection.cursor()
create_table_query = '''
CREATE TABLE "message_store" (
	"id"	INTEGER NOT NULL,
	"session_id"	TEXT,
	"message"	TEXT,
	"timestamp" DATETIME DEFAULT (datetime(CURRENT_TIMESTAMP, '+5 hours', '+30 minutes')),
	PRIMARY KEY("id")
);
'''

cursor.execute(create_table_query)
connection.commit()
connection.close()

print("user_inputs Table created successfully.")

