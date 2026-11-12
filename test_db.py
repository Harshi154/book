from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("SELECT student_id, student_name, email FROM students")
print(cursor.fetchall())

cursor.close()
conn.close()