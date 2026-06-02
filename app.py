import sqlite3
import hashlib
import json
from datetime import datetime

# Initialize the Local/Cloud Database
def init_db():
    conn = sqlite3.connect("cloud_database.db")
    cursor = conn.cursor()
    
    # Core data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verified_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_payload TEXT NOT NULL,
            data_hash TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Log table to track blocked duplicates and false positives
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempted_payload TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Generate a deterministic hash for checking data structure redundancy
def generate_data_hash(data_dict):
    # Sorting keys ensures identical JSON data yields the same hash
    serialized_data = json.dumps(data_dict, sort_keys=True)
    return hashlib.sha256(serialized_data.encode('utf-8')).hexdigest()

# Validate and ingest data into the cloud system
def process_data_ingestion(data_payload):
    conn = sqlite3.connect("cloud_database.db")
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # --- 1. VALIDATION MECHANISM ---
    # Basic structural check: Catching "False Positives" (corrupted or empty submissions)
    if not data_payload or not isinstance(data_payload, dict):
        cursor.execute(
            "INSERT INTO system_logs (attempted_payload, status, reason, timestamp) VALUES (?, ?, ?, ?)",
            (str(data_payload), "REJECTED", "False Positive: Invalid or Empty Structure", timestamp)
        )
        conn.commit()
        conn.close()
        return "❌ Rejected: False Positive / Invalid Data Format."

    # Generate the unique digital fingerprint of the data
    data_hash = generate_data_hash(data_payload)
    serialized_str = json.dumps(data_payload, sort_keys=True)

    # --- 2. IDENTIFY AND PREVENT DUPLICATES ---
    try:
        # Append only unique and verified entries
        cursor.execute(
            "INSERT INTO verified_data (data_payload, data_hash, timestamp) VALUES (?, ?, ?)",
            (serialized_str, data_hash, timestamp)
        )
        conn.commit()
        
        # Log successful entry
        cursor.execute(
            "INSERT INTO system_logs (attempted_payload, status, reason, timestamp) VALUES (?, ?, ?, ?)",
            (serialized_str, "SUCCESS", "Unique data verified and added", timestamp)
        )
        conn.commit()
        status_msg = "✅ Success: Unique data verified and appended to the cloud database."
        
    except sqlite3.IntegrityError:
        # The data_hash UNIQUE constraint failed -> Redundancy detected
        cursor.execute(
            "INSERT INTO system_logs (attempted_payload, status, reason, timestamp) VALUES (?, ?, ?, ?)",
            (serialized_str, "BLOCKED", "Redundant: Duplicate data entry detected", timestamp)
        )
        conn.commit()
        status_msg = "⚠️ Blocked: Redundant data detected. Ingestion bypassed to preserve efficiency."
        
    finally:
        conn.close()
        
    return status_msg

# --- SYSTEM SIMULATION WRAPPER ---
if __name__ == "__main__":
    init_db()
    print("--- Starting Data Redundancy Removal System Simulation ---\n")
    
    # Sample sensor/user records
    record_A = {"device_id": "sensor_01", "temperature": 22.5, "humidity": 60}
    record_B = {"device_id": "sensor_02", "temperature": 19.8, "humidity": 55}
    invalid_record = "Not a dictionary object"
    
    # Ingestion 1: New Unique Record
    print(f"Ingesting Record A: {record_A}")
    print(process_data_ingestion(record_A))
    print("-" * 50)
    
    # Ingestion 2: Try adding Record A again (Testing Redundancy Prevention)
    print(f"Ingesting Record A again: {record_A}")
    print(process_data_ingestion(record_A))
    print("-" * 50)
    
    # Ingestion 3: Corrupt Data Test (Testing False Positive Identification)
    print(f"Ingesting Invalid Format Data: '{invalid_record}'")
    print(process_data_ingestion(invalid_record))
    print("-" * 50)

    # Ingestion 4: New Unique Record B
    print(f"Ingesting Record B: {record_B}")
    print(process_data_ingestion(record_B))
    print("-" * 50)
