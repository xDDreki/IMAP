# Zadanie IMAP
## Technologia
Proponuje wykonać program w Pythonie. Przez swoją prostote, łatwość wykonania oraz kompatybilność z systemem Linux.

Do programu głownego ***`main.py`*** wykorzystam biblioteki pythona:
- imaplib - obsługa protokołu `IMAP` i wykonywanie zapytań
- json - obsługa `token.json` 
- email - zamiana tematów z zakodowanej wersji na normalny język. Parsowanie wiadomości
- os - obsługa ścieżek plików

Oraz dla programu dodatkowego ***`auth.py`***:
- moduł InstalledAppFlow z  google_auth_oauthlib.flow - do wykorzystania OAuth2 
- json - zapisywanie oraz tworzenie ``token.json``
- requests - "wyciąganie" emaila poprzez Google API oraz zdobyty token

By całe przedwsięzięcie cyklicznie pobierało emaile, wykorzystał bym `cron`-a lub `systemd timer`
## Sposób działania 
1.	Odpalenie programu
2.	Zalogowanie się przez konto Gmail i zapisanie danych (token oraz email)
3.	Połączenie z serwerem IMAP
4.	Pobranie listy nowych wiadomości
5.	Przefiltrowanie wiadomości zgodnie z wytycznymi
6.	Zapisanie tytułów w pliku .txt oraz plików z załączników
7.	Przeniesienie wiadomości do folderu OLD-RED
8.	Powtórzenie czynności od kroku nr 2 w jakimś interwale za pomocą `cron`-a`

## Zalety
- 	Wrażliwe dane (tj. hasło) jest zabezpieczone
- Możliwość dostosowania interwałów
- Pobieramy TYLKO emaile, które spełniają nasze kryteria później nad nimi operujemy.
## Zagrożenia
- 	Wysyłanie zapytań co pare / paręnaście sekund do serwera mail jest obciążające i w tym wypadku wysyłamy takie zapytania nawet gdy nie było żadnej zmiany na serwerze.

## Możliwe ulepszenia
-	Wykorzystanie innych, podobnych bibliotek np.: `imaplib2` , `aioimaplib`, by wykorzystać ich funkcje IDLE i reagować dopiero gdy wystąpi zmiana na serwerze zamiast cyklicznego sprawdzania skrzynki.
- 	Wykorzystać informacje zapisane w tokienie i odświeżać go automatycznie, by nie wymuszać reakcji użytkownika w momencie wygaśnięcia tokenu.
- 	Naprawić zapisywanie polskich znaków do subjects.txt **:c**

## Proof of Concept
Tworzę projekt w Google Cloud Platform i konfiguruje Gmail API, co da nam **`credentials.json`** 

Wykorzystując **`auth.py`** zdobywamy token,który trwa około godziny oraz email. Dostajemy też inne przydatne dane które warto wykorzystać, by program się „nie wysypał” po godzinie i pytał użytkownika o ponowne logowanie.
Chociaż nie będę tego wykazywał w PoC ale warto to mieć na uwadze. 

    from google_auth_oauthlib.flow import InstalledAppFlow

    import json
    import requests

    SCOPES = [
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ] 

importuje potrzebne biblioteki oraz definiuje zakres dostępu. 
- `https://mail.google.com/` pozwala nam uzyskać pełny dostęp zarządzania Gmailem.
- `https://www.googleapis.com/auth/userinfo.email` pozwala nam uzyskać e-mail zalogowanego użytkownika
- `openid` pozawala nam wysłać zapytanie do google API (W skrócie nie działa bez tego.)

Funkcja get_user_email():
    
    response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    return response.json().get("email")

Wysyła zapytanie do Google API OAuth2 by uzyskać email - wykorzystuje token.

Funkcja authenticate():

        flow=InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds=flow.run_local_server(host='localhost',port=8080)

    user_email = get_user_email(creds.token)

    with open("token.json", "w") as token_file:
        json.dump({
            # Jedyne aktualnie przydatne dane
            "token": creds.token,
            "email": user_email,
        }, token_file)

    print(f"Token zapisany dla użytkownika: {user_email}")

Wykorzystuje `credentials.json` i zapisuje je do `token.json` oraz wysyłam zapytanie API, by uzyskać **email**

Przechodząc do pliku `oppa.py` 

    import email.header
    import imaplib
    import json
    import email
    import os

Importuje potrzebne biblioteki (opisane wyżej)

funkcja load_token():

    try:
        with open(TOKEN_FILE, "r") as token_file:
            creds = json.load(token_file)
        return creds["token"], creds.get("email")
    except FileNotFoundError:
        print("Błąd: Plik token.json nie istnieje. Uruchom auth.py.")
        exit(1)

Otwieram plik `token.json` i zapisuje **token** oraz **email**, w razie braku token.json zwracam błąd.

funkcja decode_subject():

    decoded_parts=email.header.decode_header(subject)
    decoded_subject = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_subject += part.decode(encoding or "utf-8")
        else:
            decoded_subject += part
    return decoded_subject

Używam `decode_header` z biblioteki `email`, by przetłumaczyć temat, który później będzie wyciągany z emaili.
Zapętlam się przez cały subject sprawdzając czy część jest zapisana w bajtach (prawdopodobnie jest to polski znak) odpowiednio go dekoduje i dodaje go do ciągu znaków.

funkcja connect_to_email():

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

Wykorzystuje wcześniej utworzoną funkcje `load_token()`, by wyciągnać dane.
Przygotowuje łańcuch weryfikacji i łącze się z serwerem. W razie niepowodzenia wyświetlam błąd.
 