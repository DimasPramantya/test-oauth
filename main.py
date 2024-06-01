from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import secrets
import jwt  
import time  
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

CLIENT_SECRET_FILE = 'calendar_credentials.json'
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
REDIRECT_URI = 'https://oauth-a5ey42wesa-et.a.run.app/oauthcallback'
JWT_SECRET_KEY = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
app.add_middleware(SessionMiddleware, secret_key="your_super_secret_key")

class TokenData(BaseModel):
    token: str
    refresh_token: Optional[str]
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list

@app.get('/authorize')
async def authorize(request: Request):
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    flow.redirect_uri = REDIRECT_URI

    # Generate the authorization URL and extract the state
    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true'
    ) 

    # Store the state in the session
    request.session["state"] = state

    return RedirectResponse(authorization_url)

@app.get('/oauthcallback')
async def oauth2callback(request: Request):
    if request.query_params.get('state') != request.session.get("state"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES, state=request.query_params.get('state')
    )
    flow.redirect_uri = REDIRECT_URI

    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    
    # Store credentials in JWT token
    credentials = flow.credentials
    token = generate_token(credentials)
    
    return {"access_token": token, "token_type": "bearer"}

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
