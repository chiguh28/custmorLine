@echo off
echo Starting ngrok on port 5000...
echo Please copy the HTTPS URL (e.g., https://xxxx.ngrok-free.app) and set it in the LINE Developers Console.
echo Webhook URL 1: [Your URL]/callback/customer
echo Webhook URL 2: [Your URL]/callback/therapist
ngrok http 5000
pause
