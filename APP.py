from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
from twilio.rest import Client
from flask_cors import CORS
import math


cred = credentials.Certificate("firebasekey.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://accident-detection-backend-default-rtdb.asia-southeast1.firebasedatabase.app/'
})


account_sid = "ACc947921c74b3e9d0fdbbb3b5b036ba37"
auth_token = "7bf744881700f7e64f82047e62ee453b"
twilio_number = "+12605687460"
receiver_number = "+919344992323"

client = Client(account_sid, auth_token)

app = Flask(__name__)
CORS(app)


def calculate_severity(ax, ay, az):
    impact = (ax**2 + ay**2 + az**2) ** 0.5

    if impact < 2:
        return "LOW"
    elif impact < 5:
        return "MEDIUM"
    else:
        return "HIGH"

def calculate_tilt(ax, ay, az):
    try:
        roll = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))

        # Convert to degrees
        roll_deg = math.degrees(roll)
        pitch_deg = math.degrees(pitch)

        return round(roll_deg, 2), round(pitch_deg, 2)
    except:
        return 0, 0

def get_status(severity):
    if severity == "LOW":
        return "Minor Accident"
    elif severity == "MEDIUM":
        return "Moderate Accident"
    else:
        return "Severe Accident"

def send_sms(lat, lon, severity, status, timestamp, roll, pitch):
    try:
        message = f"""
  ACCIDENT DETECTED 
Status: {status}
Severity: {severity}
Tilt: Roll={roll}°, Pitch={pitch}°
Time: {timestamp}
Location: https://maps.google.com/?q={lat},{lon}
"""
        msg = client.messages.create(
            body=message,
            from_=twilio_number,
            to=receiver_number
        )
        print("SMS sent:", msg.sid)
    except Exception as e:
        print("SMS failed:", str(e))

def make_call(severity):
    try:
        call = client.calls.create(
            twiml=f"""
            <Response>
                <Say voice="alice">
                    Emergency! Accident detected.
                    Severity level is {severity}.
                </Say>
            </Response>
            """,
            from_=twilio_number,
            to=receiver_number
        )
        print("Call triggered:", call.sid)
    except Exception as e:
        print("Call failed:", str(e))

@app.route('/report', methods=['POST'])
def report_accident():
    try:
        data = request.json
        print("Incoming Data:", data)

        lat = data.get('latitude')
        lon = data.get('longitude')
        ax = data.get('ax')
        ay = data.get('ay')
        az = data.get('az')

        if None in [lat, lon, ax, ay, az]:
            return jsonify({"error": "Missing data"}), 400

       
        severity = calculate_severity(ax, ay, az)

        
        roll, pitch = calculate_tilt(ax, ay, az)

        
        status = get_status(severity)

        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("Severity:", severity)
        print("Tilt:", roll, pitch)

        ref = db.reference('accidents')
        ref.push({
            "latitude": lat,
            "longitude": lon,
            "severity": severity,
            "status": status,
            "timestamp": timestamp,
            "roll": roll,
            "pitch": pitch
        })

        
        send_sms(lat, lon, severity, status, timestamp, roll, pitch)

        
        if severity in ["MEDIUM", "HIGH"]:
            make_call(severity)

        return jsonify({
            "message": "Success",
            "severity": severity,
            "status": status,
            "timestamp": timestamp,
            "roll": roll,
            "pitch": pitch
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
