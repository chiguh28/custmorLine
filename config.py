import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Customer Bot Settings
    LINE_CHANNEL_SECRET_CUSTOMER = os.getenv('LINE_CHANNEL_SECRET_CUSTOMER')
    LINE_CHANNEL_ACCESS_TOKEN_CUSTOMER = os.getenv('LINE_CHANNEL_ACCESS_TOKEN_CUSTOMER')

    # Therapist Bot Settings
    LINE_CHANNEL_SECRET_THERAPIST = os.getenv('LINE_CHANNEL_SECRET_THERAPIST')
    LINE_CHANNEL_ACCESS_TOKEN_THERAPIST = os.getenv('LINE_CHANNEL_ACCESS_TOKEN_THERAPIST')

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    IMAGE_FOLDER = os.path.join(STATIC_FOLDER, 'images')
    DB_PATH = os.path.join(BASE_DIR, 'data', 'app.db')

    # Broadcast Message Template
    BROADCAST_MESSAGE_TEMPLATE = """
【出勤情報更新】
今週のスケジュールをご確認ください✨
ご予約お待ちしております!
"""
