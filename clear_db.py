

#this file should be in the same folder as the database.py file will be deleting this from this folder and putting it 
#in the other folder to avoid confusion and for uploading it to git

from database import SessionLocal, ChargingStation, Transaction
from sqlalchemy import func

def verify_table_count(session, table):
    """Return the number of rows in a table"""
    return session.query(func.count(table.id)).scalar()

def clear_and_verify_database():
    session = SessionLocal()
    try:
        # Print initial counts
        initial_transactions = verify_table_count(session, Transaction)
        initial_stations = verify_table_count(session, ChargingStation)
        
        print(f"Before deletion:")
        print(f"Transactions: {initial_transactions}")
        print(f"Charging Stations: {initial_stations}")
        
        # Delete all rows from both tables
        session.query(Transaction).delete(synchronize_session='fetch')
        session.query(ChargingStation).delete(synchronize_session='fetch')
        
        # Commit the changes
        session.commit()
        
        # Verify deletion
        final_transactions = verify_table_count(session, Transaction)
        final_stations = verify_table_count(session, ChargingStation)
        
        print(f"\nAfter deletion:")
        print(f"Transactions: {final_transactions}")
        print(f"Charging Stations: {final_stations}")
        
        if final_transactions == 0 and final_stations == 0:
            print("\nDatabase successfully cleared!")
        else:
            print("\nWarning: Some records may remain in the database!")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    response = input("This will delete ALL data from the database. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        clear_and_verify_database()
    else:
        print("Operation cancelled")