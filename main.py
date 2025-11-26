from flask import Flask, request, abort, send_from_directory, render_template, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage,
    FollowEvent, UnfollowEvent, ImageMessage,
    TemplateSendMessage, ConfirmTemplate, MessageAction,
    ButtonsTemplate, URIAction
)
import os
import uuid
import datetime
from config import Config
from database import (
    add_friend, remove_friend, get_active_friends,
    set_therapist_state, get_therapist_state, init_db,
    get_courses, get_reservations, create_reservation,
    get_monthly_income, upsert_user, get_user,
    get_all_customers, update_customer, delete_customer, is_customer_banned,
    get_user_reservations
)

# Initialize database on startup
init_db()

app = Flask(__name__)

# Customer Bot
line_bot_api_customer = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN_CUSTOMER)
handler_customer = WebhookHandler(Config.LINE_CHANNEL_SECRET_CUSTOMER)

# Therapist Bot
line_bot_api_therapist = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN_THERAPIST)
handler_therapist = WebhookHandler(Config.LINE_CHANNEL_SECRET_THERAPIST)

# Ensure image directory exists
if not os.path.exists(Config.IMAGE_FOLDER):
    os.makedirs(Config.IMAGE_FOLDER)

# Health check endpoint for Render
@app.route("/")
def health_check():
    return "OK", 200

@app.route("/callback/customer", methods=['POST'])
def callback_customer():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler_customer.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@app.route("/callback/therapist", methods=['POST'])
def callback_therapist():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler_therapist.handle(body, signature)
    except InvalidSignatureError:
        print("!!! InvalidSignatureError !!!")
        print(f"Configured Secret: {Config.LINE_CHANNEL_SECRET_THERAPIST[:4]}... (Check .env)")
        print(f"Received Signature: {signature}")
        abort(400)
    return 'OK'

# --- Web Views ---

@app.route("/booking")
def booking_page():
    user_id = request.args.get('userId')
    return render_template('booking.html', user_id=user_id, liff_id=Config.LIFF_ID, salon_location=Config.SALON_LOCATION)

@app.route("/therapist/dashboard")
def therapist_dashboard():
    return render_template('therapist_dashboard.html')

# --- API Endpoints ---

@app.route("/api/courses", methods=['GET'])
def api_courses():
    courses = get_courses()
    return jsonify([dict(row) for row in courses])

@app.route("/api/therapist/courses", methods=['POST'])
def api_therapist_courses():
    from database import upsert_course
    data = request.json
    # Expecting list of {id, name, duration, price, description}
    if not isinstance(data, list):
        data = [data]
    
    for item in data:
        upsert_course(
            item.get('id'), # None if new
            item.get('name'),
            item.get('duration'),
            item.get('price'),
            item.get('description')
        )
            
    return jsonify({'status': 'success'})

@app.route("/api/availability", methods=['GET'])
def api_availability():
    start_date_str = request.args.get('startDate') # YYYY-MM-DD
    if not start_date_str:
        return jsonify({'error': 'Start Date required'}), 400
    
    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    # Generate 7 days
    response_data = {}
    start_hour = 10
    end_hour = 20

    # Get reservations for the whole week range
    end_date = start_date + datetime.timedelta(days=6)
    reservations = get_reservations(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    # Get therapist schedules
    from database import get_therapist_schedules
    schedules = get_therapist_schedules(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    for i in range(7):
        current_date = start_date + datetime.timedelta(days=i)
        date_key = current_date.strftime('%Y-%m-%d')
        slots = []
        
        # Find schedule for this day
        day_schedule = next((s for s in schedules if s['date'] == date_key), None)
        
        if day_schedule and day_schedule['status'] == 'available':
            # Parse schedule start/end
            sched_start_h, sched_start_m = map(int, day_schedule['start_time'].split(':'))
            sched_end_h, sched_end_m = map(int, day_schedule['end_time'].split(':'))
            
            # Generate 30-minute slots based on schedule
            # Loop from 0 to 23 hours, check if within schedule
            for h in range(0, 24):
                for minute in [0, 30]:
                    # Check if time is within schedule
                    # Convert to comparable integers (minutes from midnight)
                    current_mins = h * 60 + minute
                    sched_start_mins = sched_start_h * 60 + sched_start_m
                    sched_end_mins = sched_end_h * 60 + sched_end_m
                    
                    if current_mins >= sched_start_mins and current_mins < sched_end_mins:
                        time_str = f"{h:02d}:{minute:02d}"
                        status = 'available'
                        
                        # Check existing reservations
                        for r in reservations:
                            if r['reservation_date'] == date_key:
                                # Calculate blocked end time (Reservation End + 30min buffer)
                                res_end_dt = datetime.datetime.strptime(r['end_time'], '%H:%M')
                                blocked_end_dt = res_end_dt + datetime.timedelta(minutes=30)
                                blocked_end_time = blocked_end_dt.strftime('%H:%M')
                                
                                # Check if slot start time is within [Start, Blocked End)
                                if r['start_time'] <= time_str < blocked_end_time:
                                    status = 'booked'
                                    break
                        
                        slots.append({'time': time_str, 'status': status})
        
        response_data[date_key] = slots

    return jsonify(response_data)

@app.route("/api/reservations", methods=['POST'])
def api_create_reservation():
    data = request.json
    user_id = data.get('userId')
    course_id = data.get('courseId')
    date = data.get('date')
    start_time = data.get('startTime')
    
    # Check if customer is banned
    if is_customer_banned(user_id):
        return jsonify({'error': 'Customer is banned from booking'}), 403
    
    # Calculate end_time based on course duration (simplified)
    # In real app, fetch course duration
    courses = get_courses()
    course = next((c for c in courses if c['id'] == int(course_id)), None)
    if not course:
        return jsonify({'error': 'Invalid course'}), 400
    
    duration = course['duration_minutes']
    # Simple time addition
    h, m = map(int, start_time.split(':'))
    end_dt = datetime.datetime(2000, 1, 1, h, m) + datetime.timedelta(minutes=duration)
    end_time = end_dt.strftime('%H:%M')
    
    total_price = course['price']
    
    # Upsert user info
    upsert_user(user_id, data.get('name'), data.get('phone'))
    
    success = create_reservation(user_id, course_id, date, start_time, end_time, total_price)
    
    if success:
        # Notify Therapist
        try:
            line_bot_api_therapist.broadcast(TextSendMessage(
                text=f"【新着予約】\nお客様: {data.get('name')}\n電話番号: {data.get('phone')}\n日時: {date} {start_time}\nコース: {course['name']} ({duration}分)"
            ))
        except Exception as e:
            print(f"Failed to notify therapist: {e}")

        # Notify Customer
        try:
            line_bot_api_customer.push_message(user_id, TextSendMessage(
                text=f"予約が完了しました。\n日時: {date} {start_time}\nコース: {course['name']}"
            ))
        except Exception as e:
            print(f"Failed to notify customer: {e}")

        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'Slot already booked'}), 409

@app.route("/api/therapist/data", methods=['GET'])
def api_therapist_data():
    today = datetime.date.today()
    start_date = today.replace(day=1).strftime('%Y-%m-%d')
    # End of month
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_date = today.replace(day=last_day).strftime('%Y-%m-%d')
    
    reservations = get_reservations(start_date, end_date)
    income = get_monthly_income(today.year, today.month)
    
    return jsonify({
        'reservations': [dict(row) for row in reservations],
        'income': income
    })

@app.route("/api/therapist/schedules", methods=['GET', 'POST'])
def api_therapist_schedules():
    from database import get_therapist_schedules, upsert_schedule
    
    if request.method == 'GET':
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        if not start_date or not end_date:
            return jsonify({'error': 'Dates required'}), 400
            
        schedules = get_therapist_schedules(start_date, end_date)
        return jsonify([dict(row) for row in schedules])
        
    elif request.method == 'POST':
        data = request.json
        # Expecting a list of schedules or a single one? Let's handle list.
        # data = [{date, startTime, endTime, status}, ...]
        if not isinstance(data, list):
            data = [data]
            
        for item in data:
            upsert_schedule(
                item.get('date'),
                item.get('startTime'),
                item.get('endTime'),
                item.get('status', 'available')
            )
        return jsonify({'status': 'success'})

# --- Customer Management API ---

@app.route("/api/therapist/customers", methods=['GET'])
def api_get_customers():
    customers = get_all_customers()
    return jsonify([dict(row) for row in customers])

@app.route("/api/therapist/customers/<user_id>", methods=['PUT'])
def api_update_customer(user_id):
    data = request.json
    success = update_customer(
        user_id,
        name=data.get('name'),
        phone_number=data.get('phone_number'),
        is_banned=data.get('is_banned')
    )
    if success:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'Customer not found'}), 404

@app.route("/api/therapist/customers/<user_id>", methods=['DELETE'])
def api_delete_customer(user_id):
    success = delete_customer(user_id)
    if success:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'Failed to delete customer'}), 500

@app.route("/api/customer/status/<user_id>", methods=['GET'])
def api_customer_status(user_id):
    is_banned = is_customer_banned(user_id)
    return jsonify({'is_banned': is_banned})

# --- Customer Bot Handlers ---
@handler_customer.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    add_friend(user_id)
    print(f"New friend added: {user_id}")

@handler_customer.add(UnfollowEvent)
def handle_unfollow(event):
    user_id = event.source.user_id
    remove_friend(user_id)
    print(f"Friend removed: {user_id}")

@handler_customer.add(MessageEvent, message=TextMessage)
def handle_message_customer(event):
    text = event.message.text
    user_id = event.source.user_id
    
    if text == "予約する":
        # Send Booking Link
        base_url = request.url_root.replace('http://', 'https://')
        booking_url = f"{base_url}booking?userId={user_id}"
        
        line_bot_api_customer.reply_message(
            event.reply_token,
            TemplateSendMessage(
                alt_text='予約画面を開く',
                template=ButtonsTemplate(
                    title='予約',
                    text='以下のボタンから予約してください',
                    actions=[
                        URIAction(
                            label='予約画面を開く',
                            uri=booking_url
                        )
                    ]
                )
            )
        )
    elif text == "料金表":
        # Send price list image
        base_url = request.url_root.replace('http://', 'https://')
        image_url = f"{base_url}static/images/price_list.png"
        
        line_bot_api_customer.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
        )
    elif text == "出勤表":
        # Send latest schedule image
        base_url = request.url_root.replace('http://', 'https://')
        image_url = f"{base_url}static/images/schedule_latest.png"
        
        # Check if file exists
        if os.path.exists(os.path.join(Config.IMAGE_FOLDER, 'schedule_latest.png')):
            line_bot_api_customer.reply_message(
                event.reply_token,
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            )
        else:
             line_bot_api_customer.reply_message(
                event.reply_token,
                TextSendMessage(text="現在、出勤表は準備中です。")
            )
    elif text == "予約確認":
        # Get user's reservations
        reservations = get_user_reservations(user_id)
        
        if not reservations:
            line_bot_api_customer.reply_message(
                event.reply_token,
                TextSendMessage(text="現在、予約はありません。")
            )
        else:
            # Format reservation info
            messages = []
            for res in reservations:
                message_text = f"【予約情報】\n日時: {res['reservation_date']} {res['start_time']}\nコース: {res['course_name']} ({res['duration_minutes']}分)\n場所: {Config.SALON_LOCATION}"
                messages.append(TextSendMessage(text=message_text))
            
            # Max 5 messages allowed in reply
            line_bot_api_customer.reply_message(
                event.reply_token,
                messages[:5]
            )

# --- Therapist Bot Handlers ---
@handler_therapist.add(MessageEvent, message=TextMessage)
def handle_message_therapist(event):
    user_id = event.source.user_id
    text = event.message.text
    state = get_therapist_state(user_id)

    if text == "管理":
        # Send Dashboard Link
        base_url = request.url_root.replace('http://', 'https://')
        dashboard_url = f"{base_url}therapist/dashboard"
        
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TemplateSendMessage(
                alt_text='管理画面を開く',
                template=ButtonsTemplate(
                    title='管理',
                    text='以下のボタンから管理画面を開いてください',
                    actions=[
                        URIAction(
                            label='管理画面を開く',
                            uri=dashboard_url
                        )
                    ]
                )
            )
        )

    elif text == "出勤情報登録":
        set_therapist_state(user_id, 'waiting_for_image')
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TextSendMessage(text="出勤表の画像を送信してください。")
        )
    
    elif text == "配信する" or text == "キャンセル":
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TextSendMessage(text="現在は画像を送信すると即時配信されます。")
        )

@handler_therapist.add(MessageEvent, message=ImageMessage)
def handle_image_therapist(event):
    user_id = event.source.user_id
    
    # 1. Save the image
    message_content = line_bot_api_therapist.get_message_content(event.message.id)
    file_path = os.path.join(Config.IMAGE_FOLDER, 'schedule_latest.png')
    
    with open(file_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    
    # 2. Prepare broadcast messages
    base_url = request.url_root.replace('http://', 'https://')
    image_url = f"{base_url}static/images/schedule_latest.png"
    
    messages = [
        TextSendMessage(text=Config.BROADCAST_MESSAGE_TEMPLATE.strip()),
        ImageSendMessage(
            original_content_url=image_url,
            preview_image_url=image_url
        )
    ]

    # 3. Immediate Broadcast
    try:
        line_bot_api_customer.broadcast(messages)
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TextSendMessage(text="画像を受信し、全友だちに即時配信しました。")
        )
    except Exception as e:
        print(f"Broadcast error: {e}")
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TextSendMessage(text="配信中にエラーが発生しました。")
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(port=port)
