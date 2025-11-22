import os
from unittest.mock import MagicMock, patch

# Set dummy env vars before importing main
os.environ['LINE_CHANNEL_ACCESS_TOKEN_CUSTOMER'] = 'test_token_customer'
os.environ['LINE_CHANNEL_SECRET_CUSTOMER'] = 'test_secret_customer'
os.environ['LINE_CHANNEL_ACCESS_TOKEN_THERAPIST'] = 'test_token_therapist'
os.environ['LINE_CHANNEL_SECRET_THERAPIST'] = 'test_secret_therapist'

import unittest
import json
from main import app, handle_message_customer, handle_message_therapist
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from database import init_db, add_friend, get_active_friends, set_therapist_state, get_therapist_state

class TestLineBot(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        init_db()
        
        # Mock LINE API
        self.mock_line_bot_api_customer = MagicMock()
        self.mock_line_bot_api_therapist = MagicMock()
        
        # Patch the global API objects in main
        patcher1 = patch('main.line_bot_api_customer', self.mock_line_bot_api_customer)
        patcher2 = patch('main.line_bot_api_therapist', self.mock_line_bot_api_therapist)
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        patcher1.start()
        patcher2.start()

    def test_database_friends(self):
        add_friend('user123')
        friends = get_active_friends()
        self.assertIn('user123', friends)

    def test_therapist_state(self):
        set_therapist_state('therapist1', 'waiting_for_image')
        state = get_therapist_state('therapist1')
        self.assertEqual(state, 'waiting_for_image')

    def test_customer_price_list(self):
        # Simulate "料金表" message
        event = MagicMock()
        event.reply_token = 'token'
        event.message.text = '料金表'
        
        # We need to mock request.url_root since it's used in the handler
        with app.test_request_context():
            handle_message_customer(event)
        
        self.mock_line_bot_api_customer.reply_message.assert_called_once()
        args = self.mock_line_bot_api_customer.reply_message.call_args[0]
        self.assertIsInstance(args[1], ImageSendMessage)
        self.assertIn('price_list.png', args[1].original_content_url)

    def test_therapist_flow_start(self):
        # Simulate "出勤情報登録"
        event = MagicMock()
        event.source.user_id = 'therapist1'
        event.reply_token = 'token'
        event.message.text = '出勤情報登録'
        
        handle_message_therapist(event)
        
        self.assertEqual(get_therapist_state('therapist1'), 'waiting_for_image')
        self.mock_line_bot_api_therapist.reply_message.assert_called_once()
        args = self.mock_line_bot_api_therapist.reply_message.call_args[0]
        self.assertEqual(args[1].text, "出勤表の画像を送信してください。")

if __name__ == '__main__':
    unittest.main()
