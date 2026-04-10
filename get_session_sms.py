from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

API_ID   = 35507477
API_HASH = "201ab47b2a808cc66c3ef61529dba649"

client = TelegramClient(StringSession(), API_ID, API_HASH)
client.connect()

phone = input("Telefon: ").strip()
sent = client.send_code_request(phone, force_sms=True)
print(f"Kod yuborildi!")

code = input("Kod: ").strip()

try:
    client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
except SessionPasswordNeededError:
    pw = input("2FA parol: ").strip()
    client.sign_in(password=pw)

print("\n===== SESSION STRING =====")
print(client.session.save())
print("==========================\n")
client.disconnect()
