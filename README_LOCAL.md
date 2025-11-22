# Local Testing & Ngrok Deployment Guide

## 1. Setup Environment
Ensure all dependencies are installed (I have already done this for you, but just in case):
```bash
pip install -r requirements.txt
```

## 2. Run Local Tests
To verify the logic without connecting to LINE:
```bash
python test_local.py
```
(You should see "OK" at the end)

## 3. Start the Application
Run the following batch file to start the Flask server:
- `start_app.bat`

## 4. Start Ngrok
Run the following batch file to expose your local server to the internet:
- `start_ngrok.bat`

**Important:**
1.  Copy the HTTPS URL from the ngrok window (e.g., `https://abcd-1234.ngrok-free.app`).
2.  Go to the [LINE Developers Console](https://developers.line.biz/).
3.  Update the Webhook URL for your bots:
    - **Customer Bot**: `[Your Ngrok URL]/callback/customer`
    - **Therapist Bot**: `[Your Ngrok URL]/callback/therapist`
4.  Enable "Use Webhook".

## 5. Configure Environment Variables
You need to set your actual LINE Channel Secrets and Access Tokens.
Open the `.env` file in `d:\02.Tool\custmorLine\` and fill in your actual keys:

```
LINE_CHANNEL_SECRET_CUSTOMER=your_customer_secret
LINE_CHANNEL_ACCESS_TOKEN_CUSTOMER=your_customer_token
LINE_CHANNEL_SECRET_THERAPIST=your_therapist_secret
LINE_CHANNEL_ACCESS_TOKEN_THERAPIST=your_therapist_token
```
