from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
import secrets
import jwt  
import time  
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Set up CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

CLIENT_SECRET_FILE = 'calendar_credentials.json'
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
REDIRECT_URI = 'https://665b46e22a9143cd55a24c29--rococo-florentine-b63072.netlify.app/'
JWT_SECRET_KEY = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"

@app.post('/exchange')
async def exchange_code(code: str):
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE, scopes=SCOPES
        )
        flow.fetch_token(code=code)

        credentials = flow.credentials
        token = generate_token(credentials)

        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

@app.get('/calendar')
async def testGoogleCalendar(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    creds = Credentials(
        token=user['token'],
        refresh_token=user.get('refresh_token'),
        token_uri=user['token_uri'],
        client_id=user['client_id'],
        client_secret=user['client_secret'],
        scopes=user['scopes']
    )

    service = build("calendar", "v3", credentials=creds)
    now = datetime.now()
    event_start = now + timedelta(days=1)
    event_end = event_start + timedelta(hours=2)
    attendee_email = "igkdimas@gmail.com"
    event = {
        "summary": "Test",
        "start": {"dateTime": event_start.isoformat() + 'Z', "timeZone": "America/New_York"},
        "end": {"dateTime": event_end.isoformat() + 'Z', "timeZone": "America/New_York"},
        "attendees": [{"email": attendee_email}]
    }
    event = service.events().insert(calendarId="primary", body=event).execute()
    return {"message": "Event created successfully"}

def generate_token(credentials):
    payload = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "exp": int(time.time()) + 3600  # Token expiration (1 hour)
    }
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
