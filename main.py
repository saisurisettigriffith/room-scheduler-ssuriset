from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore
from fastapi import Form
import google.oauth2.id_token
from fastapi.responses import RedirectResponse
import datetime


app = FastAPI()

firebase_request_adapter = requests.Request()

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")
db = firestore.Client()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    id_token = request.cookies.get("token")
    user_token = None
    exp_current_user_specific_room = []

    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))

    bookings_query_raw = db.collection('bookings').get()
    rooms_query_raw = db.collection('rooms').get()
   
    exp_rooms = [{'id': doc.id, 'email': doc.to_dict().get('email', 'No email provided'), 'room_name': doc.to_dict()['room_name'], 'bookings': []} for doc in rooms_query_raw]

    selected_date = request.query_params.get("date-rooms-all-bookings")

    for room in exp_rooms:
        bookings_query_raw = db.collection('bookings').where('room_id', '==', room['id'])
        if selected_date:
            bookings_query_raw = bookings_query_raw.where('date', '==', selected_date)
        bookings_query_raw = bookings_query_raw.get()
        room_bookings = [{'id': doc.id, **doc.to_dict()} for doc in bookings_query_raw]
        sorted_room_bookings = sorted(room_bookings, key=lambda x: x['start_time'])
        room['bookings'] = sorted_room_bookings

    exp_current_user = []

    user_email = user_token['email'] if user_token else None

    if user_email:
        bookings_query_raw = db.collection('bookings').where('email', '==', user_email).get()
        exp_current_user = []
        for doc in bookings_query_raw:
            booking_data = doc.to_dict()
            room_id = booking_data['room_id']
            room_doc = db.collection('rooms').document(room_id).get()
            if room_doc.exists:
                room_name = room_doc.to_dict().get('room_name', 'ERROR: Room Name Not Found')
            else:
                room_name = 'ERROR: Room Not Found'
            exp_current_user.append({'id': doc.id, 'room_name': room_name, **booking_data})

    room_select_a = request.query_params.get('room-select-a')

    if user_email and room_select_a:
        rooms_query_raw = db.collection('rooms').where('room_name', '==', room_select_a).get()
        if rooms_query_raw:
            room_id = rooms_query_raw[0].id
            room_name = rooms_query_raw[0].to_dict().get('room_name')
            bookings_query_raw = db.collection('bookings').where('room_id', '==', room_id).where('email', '==', user_email).get()
            exp_current_user_specific_room = [{'id': doc.id, 'room_name': room_name, **doc.to_dict()} for doc in bookings_query_raw]

    return templates.TemplateResponse('main.html', {
        'request': request, 
        'user_token': user_token,
        'exp_rooms': exp_rooms, 
        'exp_current_user': exp_current_user, 
        'exp_current_user_specific_room': exp_current_user_specific_room,
        'selected_date': selected_date
    })

@app.get("/page-booking", response_class=HTMLResponse)
async def PAGEbooking(request: Request):
    id_token = request.cookies.get("token")
    user_token = None

    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)

    rooms_query_raw = db.collection('rooms').get()
    
    if not rooms_query_raw:
        return RedirectResponse(url="/", status_code=404)
    
    exp_rooms = [doc.to_dict() for doc in rooms_query_raw]

    return templates.TemplateResponse('booking.html', {'request': request, 'user_token': user_token, 'exp_rooms': exp_rooms})

@app.post("/post-booking", response_class=HTMLResponse)
async def POSTbooking(request: Request, name: str = Form(...), date: str = Form(...), start_time: str = Form(...), end_time: str = Form(...), room: str = Form(...)):
    batch = db.batch()
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)

    rooms_query_raw = db.collection('rooms').where('room_name', '==', room).get()
    room_id = rooms_query_raw[0].id

    temp_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    temp_start_time = datetime.datetime.strptime(start_time, "%H:%M").time()
    temp_end_time = datetime.datetime.strptime(end_time, "%H:%M").time()

    bookings_query_raw = db.collection('bookings').where('room_id', '==', room_id).get()
    for doc in bookings_query_raw:
        booking = doc.to_dict()
        booking_date = datetime.datetime.strptime(booking['date'], "%Y-%m-%d").date()
        booking_start_time = datetime.datetime.strptime(booking['start_time'], "%H:%M").time()
        booking_end_time = datetime.datetime.strptime(booking['end_time'], "%H:%M").time()
        
        if booking_date == temp_date:
            if not (temp_end_time <= booking_start_time or temp_start_time >= booking_end_time):
                return RedirectResponse(url="/", status_code=404)

    if temp_start_time >= temp_end_time:
        return RedirectResponse(url="/", status_code=404)

    current_datetime = datetime.datetime.now()
    if temp_date < current_datetime.date() or (temp_date == current_datetime.date() and (temp_start_time < current_datetime.time() or temp_end_time < current_datetime.time())):
        return RedirectResponse(url="/", status_code=404)

    doc_query_raw = db.collection('bookings').document()
    doc_query_raw.set({
        'name': name,
        'email': user_token['email'],
        'date': date,
        'start_time': start_time,
        'end_time': end_time,
        'room_id': room_id
    })
    
    room_query_raw = db.collection('rooms').document(room_id)
    batch.update(room_query_raw, {
        'booking_ids': firestore.ArrayUnion([doc_query_raw.id])
    })

    batch.commit()

    return RedirectResponse(url="/", status_code=303)

@app.get("/page-addingroom", response_class=HTMLResponse)
async def PAGEaddingroom(request: Request):
    id_token = request.cookies.get("token")
    user_token = None

    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)

    return templates.TemplateResponse('addingroom.html', {'request': request, 'user_token': user_token})

@app.post("/post-addingroom", response_class=HTMLResponse)
async def POSTaddingroom(request: Request, room_name: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)
    
    doc_query_raw = db.collection('rooms').document()
    existing_rooms_query_raw = db.collection('rooms').where('room_name', '==', room_name).get()

    if existing_rooms_query_raw:
        return RedirectResponse(url="/", status_code=404)
    else:
        doc_query_raw.set({
            'room_name': room_name,
            'email': user_token['email']
        })
        doc_query_raw.update({
            'booking_ids': []
        })
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete-booking", response_class=HTMLResponse)
async def DELETEbooking(request: Request, booking_id: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)

    if user_token:
        booking_query_raw = db.collection('bookings').document(booking_id)
        booking_doc = booking_query_raw.get()
        if booking_doc.exists:
            booking_data = booking_doc.to_dict()
            if booking_data['email'] == user_token['email']:
                booking_query_raw.delete()
                room_id = booking_data.get('room_id')
                if room_id:
                    room_doc_ref = db.collection('rooms').document(room_id)
                    room_doc_ref.update({
                        'booking_ids': firestore.ArrayRemove([booking_id])
                    })

    return RedirectResponse(url="/", status_code=303)

@app.post("/page-edit-booking-user", response_class=HTMLResponse)
async def PAGEeditbookinguser(request: Request, booking_id: str = Form(...), booking_name: str = Form(...), booking_email: str = Form(...), booking_room_id: str = Form(...), booking_date: str = Form(...), booking_start_time: str = Form(...), booking_end_time: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)
    if user_token:
        if booking_email != user_token['email']:
            return RedirectResponse(url="/", status_code=404)
    return templates.TemplateResponse('editbookinguser.html', {'request': request, 'booking_id': booking_id, 'booking_name': booking_name, 'booking_email': booking_email, 'booking_room_id': booking_room_id, 'booking_date': booking_date, 'booking_start_time': booking_start_time, 'booking_end_time': booking_end_time})

@app.post("/post-edit-booking-user", response_class=HTMLResponse)
async def POSTeditbookinguser(request: Request, new_booking_id: str = Form(...), new_name: str = Form(...), new_booking_room_id: str = Form(...), new_booking_date: str = Form(...), new_booking_start_time: str = Form(...), new_booking_end_time: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)

    booking_to_edit = db.collection('bookings').document(new_booking_id).get()
    if not booking_to_edit.exists:
        return RedirectResponse(url="/", status_code=404)
    booking_data = booking_to_edit.to_dict()

    new_date = datetime.datetime.strptime(new_booking_date, "%Y-%m-%d").date()
    new_start_time = datetime.datetime.strptime(new_booking_start_time, "%H:%M").time()
    new_end_time = datetime.datetime.strptime(new_booking_end_time, "%H:%M").time()

    if new_start_time >= new_end_time:
        return RedirectResponse(url="/", status_code=404)

    current_datetime = datetime.datetime.now()
    if new_date < current_datetime.date() or (new_date == current_datetime.date() and (new_start_time < current_datetime.time() or new_end_time < current_datetime.time())):
        return RedirectResponse(url="/", status_code=404)

    existing_bookings = db.collection('bookings').where('room_id', '==', new_booking_room_id).where('date', '==', new_booking_date).get()

    for doc in existing_bookings:
        if doc.id != new_booking_id:
            existing = doc.to_dict()
            existing_start = datetime.datetime.strptime(existing['start_time'], "%H:%M").time()
            existing_end = datetime.datetime.strptime(existing['end_time'], "%H:%M").time()
            if not (new_end_time <= existing_start or new_start_time >= existing_end):
                return RedirectResponse(url="/", status_code=404)

    db.collection('bookings').document(new_booking_id).update({
        'name': new_name,
        'date': new_booking_date,
        'start_time': new_booking_start_time,
        'end_time': new_booking_end_time
    })

    return RedirectResponse(url="/", status_code=303)

@app.post("/delete-room", response_class=HTMLResponse)
async def POSTdeleteroom(request: Request, room_id: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
            return RedirectResponse(url="/", status_code=404)
        
    if user_token:
        room_query_raw = db.collection('rooms').document(room_id)
        room_doc = room_query_raw.get()
        if room_doc.exists:
            room_data = room_doc.to_dict()
            if room_data['email'] == user_token['email']:
                if room_data['booking_ids']:
                    return RedirectResponse(url="/", status_code=404)
                else:
                    room_query_raw.delete()
            else:
                return RedirectResponse(url="/", status_code=404)
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/room/{room_id}", response_class=HTMLResponse)
async def room_details(request: Request, room_id: str):
    id_token = request.cookies.get("token")
    user_token = None
    room = db.collection('rooms').document(room_id).get()
    if not room.exists:
        return RedirectResponse(url="/", status_code=404)
    room_data = room.to_dict()

    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError:
            user_token = None

    ISroomowner = user_token and room_data['email'] == user_token['email']
    
    bookings_query_raw = db.collection('bookings').where('room_id', '==', room_id).get()
    bookings = [{'id': doc.id, **doc.to_dict()} for doc in bookings_query_raw]

    return templates.TemplateResponse("roompage.html", {
        "request": request,
        "room": room_data,
        "room_id": room_id,
        "ISroomowner": ISroomowner,
        "bookings": bookings
    })