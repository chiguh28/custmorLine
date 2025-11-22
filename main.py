from flask import Flask, request, abort, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage,
    FollowEvent, UnfollowEvent, ImageMessage
)
import os
import uuid
from config import Config
from database import (
    add_friend, remove_friend, get_active_friends,
    set_therapist_state, get_therapist_state
)

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
        abort(400)
    return 'OK'

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
    
    if text == "料金表":
        # Send price list image
        # Assuming the server URL will be configured later or using a public URL
        # For now, we'll construct a URL based on the request host if possible, or use a placeholder
        # In production, this should be the full HTTPS URL of the deployed app
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

# --- Therapist Bot Handlers ---
@handler_therapist.add(MessageEvent, message=TextMessage)
def handle_message_therapist(event):
    user_id = event.source.user_id
    text = event.message.text
    state = get_therapist_state(user_id)

    if text == "出勤情報登録":
        set_therapist_state(user_id, 'waiting_for_image')
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TextSendMessage(text="出勤表の画像を送信してください。")
        )
    
    elif text == "配信する":
        if state == 'confirm_broadcast':
            # Broadcast to all friends
            friends = get_active_friends()
            if not friends:
                line_bot_api_therapist.reply_message(
                    event.reply_token,
                    TextSendMessage(text="配信対象の友だちがいません。")
                )
                return

            # Prepare messages
            base_url = request.url_root.replace('http://', 'https://')
            image_url = f"{base_url}static/images/schedule_latest.png"
            
            messages = [
                TextSendMessage(text=Config.BROADCAST_MESSAGE_TEMPLATE.strip()),
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            ]

            # Multicast (send to list of user_ids)
            # Note: split into chunks of 500 if needed (LINE API limit), but for now assuming small scale
            try:
                line_bot_api_customer.multicast(friends, messages)
                line_bot_api_therapist.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"{len(friends)}名に配信完了しました。")
                )
            except Exception as e:
                print(f"Broadcast error: {e}")
                line_bot_api_therapist.reply_message(
                    event.reply_token,
                    TextSendMessage(text="配信中にエラーが発生しました。")
                )
            
            set_therapist_state(user_id, None) # Reset state
        else:
            line_bot_api_therapist.reply_message(
                event.reply_token,
                TextSendMessage(text="「出勤情報登録」から始めてください。")
            )

    elif text == "キャンセル":
        set_therapist_state(user_id, None)
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TextSendMessage(text="操作をキャンセルしました。")
        )

@handler_therapist.add(MessageEvent, message=ImageMessage)
def handle_image_therapist(event):
    user_id = event.source.user_id
    state = get_therapist_state(user_id)

    if state == 'waiting_for_image':
        message_content = line_bot_api_therapist.get_message_content(event.message.id)
        file_path = os.path.join(Config.IMAGE_FOLDER, 'schedule_latest.png')
        
        with open(file_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        
        set_therapist_state(user_id, 'confirm_broadcast')
        
        # Confirmation message
        friends_count = len(get_active_friends())
        confirm_msg = f"""画像を受け取りました。
配信対象: {friends_count}名

この内容で配信しますか？
「配信する」または「キャンセル」と送信してください。"""
        
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TextSendMessage(text=confirm_msg)
        )

if __name__ == "__main__":
    app.run(port=5000)
