import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from tabulate import tabulate

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
db_client = create_client(SUPABASE_URL, SUPABASE_KEY)

USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"

def inspect_library():
    print(f"Inspecting Library for User: {USER_ID}\n")

    # Fetch Books
    books = db_client.table("Atoms").select("name, metadata").eq("user_id", USER_ID).eq("type", "book").execute()
    
    # Fetch People
    people = db_client.table("Atoms").select("name, metadata").eq("user_id", USER_ID).eq("type", "person").execute()

    print("--- THE ANTI-LIBRARY (Type: BOOK) ---")
    if books.data:
        book_rows = [[b['name'], b['metadata'].get('description', '')[:50] + "..."] for b in books.data]
        print(tabulate(book_rows, headers=["Title", "Description"], tablefmt="grid"))
    else:
        print("No books found.")

    print("\n--- DRAMATIS PERSONAE (Type: PERSON) ---")
    if people.data:
        person_rows = [[p['name'], p['metadata'].get('description', '')[:50] + "..."] for p in people.data]
        print(tabulate(person_rows, headers=["Name", "Role/Context"], tablefmt="grid"))
    else:
        print("No people found.")

if __name__ == "__main__":
    inspect_library()
