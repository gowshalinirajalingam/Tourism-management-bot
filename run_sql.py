import sqlite3

connection = sqlite3.connect('Digital_Tourism.db')
cursor = connection.cursor()
query = '''
Delete from message_store where session_id in ("94762319425","94775899734","94773275640","94740898346");
'''

cursor.execute(query)
connection.commit()
connection.close()

connection = sqlite3.connect('Digital_Tourism.db')
cursor = connection.cursor()
query = '''
 DELETE FROM user_inputs WHERE Phone_num="94762319425";
'''

cursor.execute(query)
connection.commit()
connection.close()


