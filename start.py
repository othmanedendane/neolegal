from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.pdfgen import canvas
import jwt

app = FastAPI()

# connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]
users_collection = db["users"]

# configure JWT settings
JWT_SECRET_KEY = "mysecretkey"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_TIME_MINUTES = 30

# create a Pydantic model for user authentication
class UserAuth(BaseModel):
    username: str
    password: str

# create a Pydantic model for the user response
class UserResponse(BaseModel):
    username: str
    firstname: str
    lastname: str

# endpoint for user authentication
@app.post("/authenticate")
async def authenticate_user(user_auth: UserAuth):
    # check if the user exists
    user = users_collection.find_one({"username": user_auth.username})
    if user is None or user_auth.password != user["password"]:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    # generate JWT token
    jwt_payload = {
        "sub": user_auth.username,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_TIME_MINUTES),
    }
    jwt_token = jwt.encode(jwt_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    # return JWT token
    return {"token": jwt_token}

# endpoint to get users filtered by username
@app.get("/users")
async def get_users(token: str, filter: str, download: str = None):
    try:
        # decode the token
        jwt_payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        if download == "pdf":
            # retrieve filtered users from MongoDB
            users = users_collection.find({"username": filter})
            # create a list of tuples containing the user data
            data = [(user["username"], user["firstname"], user["lastname"]) for user in users]
            
            # generate the PDF file
            pdf_buffer = BytesIO()
            pdf_canvas = canvas.Canvas(pdf_buffer)
            # set the position of the first row
            y = 750
            # iterate over the user data and add it to the PDF
            for username, firstname, lastname in data:
                pdf_canvas.drawString(100, y, username)
                pdf_canvas.drawString(200, y, firstname)
                pdf_canvas.drawString(300, y, lastname)
                # move to the next row
                y -= 50
            pdf_canvas.save()
            pdf_buffer.seek(0)
            # return the PDF file as a StreamingResponse
            return StreamingResponse(pdf_buffer, media_type="application/pdf")
        
        else:
            # retrieve filtered users from MongoDB
            users = users_collection.find({"username": filter})
            # create a list of usernames
            usernames = []
            for user in users:
                usernames.append(user["username"])
            # return the list of usernames in the JSON response
            return usernames
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")