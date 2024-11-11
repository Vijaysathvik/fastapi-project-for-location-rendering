import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

# Initialize FastAPI
app = FastAPI()

# Define the data model for incoming data
class LocationData(BaseModel):
    latitude: float
    longitude: float
    phone_number: str  # Add phone number to the model

# Helper function to fetch nearby police stations
def fetch_nearby_police_stations(latitude: float, longitude: float):
    if not api_key:
        raise HTTPException(status_code=500, detail="API key is missing.")
    
    url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
        f"location={latitude},{longitude}&radius=5000&type=police&key={api_key}"
    )
    response = requests.get(url)
    # return response.json()
    if response.status_code == 200:
        # Extract relevant information from the API response
        results = response.json().get("results", [])
        police_stations = [
            {
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "location": place.get("geometry", {}).get("location"),
            }
            for place in results
        ]
        return police_stations
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch police stations.")

# Helper function to send SMS alert
def send_sms_alert(phone_number: str, message: str):
    if not all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
        raise HTTPException(status_code=500, detail="Twilio credentials are missing.")
    
    client = Client(twilio_account_sid, twilio_auth_token)
    try:
        message = client.messages.create(
            body=message,
            from_=twilio_phone_number,
            to=phone_number
        )
        return message.sid  # Return the message SID as confirmation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")

# Define an endpoint to receive location data, find police stations, and send an SMS alert
@app.post("/send-alert")
async def send_alert(location: LocationData):
    try:
        # Fetch nearby police stations
        police_stations = fetch_nearby_police_stations(location.latitude, location.longitude)
        
        # Create alert message with police station information
        station_info = "\n".join(
            [f"{station['name']}, {station['address']}" for station in police_stations[:3]]
        )
        alert_message = f"Alert! Nearby police stations:\n{station_info}"

        # Send SMS alert
        sms_sid = send_sms_alert(location.phone_number, alert_message)
        
        return {
            "police_stations": police_stations,
            "sms_sid": sms_sid,
            "status": "Alert sent successfully via SMS"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
