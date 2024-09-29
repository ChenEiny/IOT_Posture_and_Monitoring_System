import sqlite3

db_path = 'iot_data.db'

def view_data():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data")
    rows = cursor.fetchall()
    
    for row in rows:
        print(row)
    
    conn.close()

if __name__ == "__main__":
    view_data()
