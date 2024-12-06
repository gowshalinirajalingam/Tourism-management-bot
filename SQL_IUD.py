import sqlite3
import pandas as pd


def get_user_records(received_phone_num, columns):
	# Connect to SQLite database
	connection = sqlite3.connect('Digital_Tourism.db')
	connection.row_factory = sqlite3.Row
	cursor = connection.cursor()

	check_record_query = f'''
SELECT {columns} FROM user_inputs WHERE Phone_num = ?;
	'''
	cursor.execute(check_record_query, (received_phone_num,))

	rows = cursor.fetchall()
	records = [dict(row) for row in rows]
	
	connection.commit()
	connection.close()

	return records

def get_chat_records(received_phone_num, columns):
	# Connect to SQLite database
	connection = sqlite3.connect('Digital_Tourism.db')
	connection.row_factory = sqlite3.Row
	cursor = connection.cursor()

	check_record_query = f'''
SELECT {columns} FROM message_store WHERE session_id = ?;
	'''
	cursor.execute(check_record_query, (received_phone_num,))

	rows = cursor.fetchall()
	records = [dict(row) for row in rows]
	
	connection.commit()
	connection.close()

	return records

def get_records(query):
	# Connect to SQLite database
	connection = sqlite3.connect('Digital_Tourism.db')
	connection.row_factory = sqlite3.Row
	cursor = connection.cursor()
	
	cursor.execute(query)

	rows = cursor.fetchall()
	records = [dict(row) for row in rows]
	
	connection.commit()
	connection.close()

	return records

def get_records_df(query):
	# Connect to SQLite database
	connection = sqlite3.connect('Digital_Tourism.db')
	df = pd.read_sql_query(query, connection)
	df_filtered = df[['Day', 'Location', 'Hotels', 'Meal', 'Room_Category']]
	df_filtered = df_filtered.drop_duplicates()
	connection.commit()
	connection.close()

	return df_filtered

def get_media_id(days, month):
	connection = sqlite3.connect('Digital_Tourism.db')
	connection.row_factory = sqlite3.Row
	cursor = connection.cursor()
	
	query = f'''
SELECT media_id FROM itinerary_media_id WHERE days = {days} and month LIKE "%{month}%";
	'''
	cursor.execute(query)

	rows = cursor.fetchall()
	records = [dict(row) for row in rows]
	
	connection.commit()
	connection.close()

	return records



def update_record(query):
	connection = sqlite3.connect('Digital_Tourism.db')
	cursor = connection.cursor()
	update_record_query = query
	print("\n======================\n", update_record_query,"\n======================")
	cursor.execute(update_record_query)
	connection.commit()
	connection.close()

def delete_record(query):
	connection = sqlite3.connect('Digital_Tourism.db')
	cursor = connection.cursor()
	delete_record_query = query
	print("\n======================\n", delete_record_query,"\n======================")
	cursor.execute(delete_record_query)
	connection.commit()
	connection.close()

def getQuesAns(query):
    # Connect to SQLite database
    connection = sqlite3.connect('Digital_Tourism.db')
    df = pd.read_sql_query(query, connection)
    context = df.to_string()
    connection.commit()
    connection.close()
    return context

