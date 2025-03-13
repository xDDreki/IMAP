import email.header
import imaplib
import json
import email
import os

IMAP_SERVER = "imap.gmail.com"
SAVE_DIR = "./emails"
FOLDER_SOURCE = "INBOX"
FOLDER_TARGET = "[Gmail]/OLD-RED"
TOKEN_FILE = "token.json"
SUBJECTS_FILE = "subjects.txt"

# Tworzenie folderu na załączniki, jeśli nie istnieje
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


# Ładuje token 
def load_token():
    try:
        with open(TOKEN_FILE, "r") as token_file:
            creds = json.load(token_file)
        return creds["token"], creds.get("email")
    except FileNotFoundError:
        print("Błąd: Plik token.json nie istnieje. Uruchom auth.py.")
        exit(1)


# Zamienia tytuł maila z formatu Base64 na normalny
def decode_subject(subject):
    decoded_parts = email.header.decode_header(subject)
    decoded_subject = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_subject += part.decode(encoding or "utf-8")
        else:
            decoded_subject += part
    return decoded_subject

# Łączy się z serwerem IMAP za pomocą tokenu
def connect_to_email():
    access_token, imap_user = load_token()

    if not imap_user:
        print("Błąd: Brak adresu e-mail w token.json.")
        exit(1)

    print(f"Logowanie do IMAP jako {imap_user}")
    auth_string = f"user={imap_user}\x01auth=Bearer {access_token}\x01\x01"

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.authenticate("XOAUTH2", lambda _: auth_string)
        print("Połączenie z IMAP nawiązane.")
        return mail
    except imaplib.IMAP4.error as e:
        print(f"Błąd logowania IMAP: {e}")
        exit(1)

# Wyciąga załącznik z wiadomości
def get_attachment(msg):
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename()
            if filename:
                filepath = os.path.join(SAVE_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))

                print(f"Zapisano załącznik: {filename}")

# Pobiera i przetwarza e-maile
def process_emails():
    mail = connect_to_email()

    # Pobranie tylko wiadomości z konkretnego folderu (INBOX)
    status, _ = mail.select(FOLDER_SOURCE)
    if status != "OK":
        print(f"Błąd wyboru folderu {FOLDER_SOURCE}.")
        return

    print(f"Szukam wiadomości zawierających [RED] w temacie...")

    # Pobranie tylko wiadomości z tematem "[RED]"
    status, messages = mail.search(None, '(SUBJECT "[RED]")')
    if status != "OK":
        print("Błąd podczas wyszukiwania wiadomości.")
        return

    message_ids = messages[0].split()
    email_count = 0

    #Iterowanie po każdej wiadomości która spełnia kryteria.
    for num in message_ids:
        status, msg_data = mail.fetch(num, "(RFC822)")

        if status != "OK":
            print(f"Błąd pobierania wiadomości {num}.")
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        #Zapisanie tematu do subjects.txt
        subject = decode_subject(msg["subject"])
        if subject:
            email_count += 1
            with open(SUBJECTS_FILE, 'a') as subj:
                subj.write(f"{subject}\n")

            print(f"Znaleziono wiadomość: {subject}")

            get_attachment(msg)

            # Przeniesienie wiadomości do OLD-RED
            mail.store(num, "+X-GM-LABELS", FOLDER_TARGET)
            mail.store(num, "+FLAGS", "\\Deleted")  # Oznaczenie do usunięcia
            print(f"Wiadomość przeniesiona do {FOLDER_TARGET}")

    mail.expunge()  # Usunięcie oznaczonych wiadomości
    mail.logout() # Wylogowanie się z maila

    if email_count > 0:
        print(f"Przetworzono {email_count} wiadomości.")
    else:
        print("Brak wiadomości do przetworzenia.")


# Uruchomienie programu
process_emails()
