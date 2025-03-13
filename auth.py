from google_auth_oauthlib.flow import InstalledAppFlow
import json
import requests

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid" #Nie działa bez openid!!! 
]

#Wysyłanie zapytania na bazie tokenu, by wyciągnąć email
def get_user_email(access_token):
    response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json().get("email")

#OAuth i później zapisuje token i e-mail użytkownika.
def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(host='localhost',port=8080)

    user_email = get_user_email(creds.token)
    with open("token.json", "w") as token_file:
        json.dump({
            # Jedyne aktualnie przydatne dane
            "token": creds.token,
            "email": user_email,
            # Przydatne w przyszłości do rozbudowy
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }, token_file)

    print(f"Token zapisany dla użytkownika: {user_email}")

#Uruchomienie progrmu
authenticate()
