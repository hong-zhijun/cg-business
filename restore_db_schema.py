import sqlite3
from database import DATABASE_PATH

def migrate():
    print(f"Connecting to database at {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(member_notes)")
    columns = [info[1] for info in cursor.fetchall()]
    
    print(f"Current columns in member_notes: {columns}")
    
    # Add email
    if 'email' not in columns:
        print("Adding email column...")
        cursor.execute("ALTER TABLE member_notes ADD COLUMN email TEXT")
        
    # Add role
    if 'role' not in columns:
        print("Adding role column...")
        cursor.execute("ALTER TABLE member_notes ADD COLUMN role TEXT")
        
    # Add source
    if 'source' not in columns:
        print("Adding source column...")
        cursor.execute("ALTER TABLE member_notes ADD COLUMN source TEXT")

    # Add join_time
    if 'join_time' not in columns:
        print("Adding join_time column...")
        cursor.execute("ALTER TABLE member_notes ADD COLUMN join_time INTEGER")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
