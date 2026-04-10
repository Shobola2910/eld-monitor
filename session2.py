from pyrogram import Client

API_ID   = 35507477
API_HASH = "201ab47b2a808cc66c3ef61529dba649"

app = Client("my_session", api_id=API_ID, api_hash=API_HASH)

with app:
    print("\n===== SESSION STRING =====")
    print(app.export_session_string())
    print("==========================\n")