# Python-flask — Final Project (RONGYUTHSOMRANG store)

A small Flask e-commerce site: products, a cookie-based cart, checkout that
notifies a Telegram group, plus user accounts (register / login / reset).

## Setup

1. Create/activate a virtual environment, then install dependencies:
       pip install -r requirements.txt

2. In `app.py`, fill in your credentials near the top:
   - TELEGRAM_TOKEN     = your BotFather token
   - TELEGRAM_CHAT_ID   = your group id (e.g. '-5105045764')
   - MAIL_USERNAME / MAIL_PASSWORD  (optional — only needed for real reset emails;
     use a Gmail App Password, not your normal password)

3. Run it:
       python app.py
   Open http://127.0.0.1:5000

## Features
- Home / Products / Product detail
- Register, Login, Logout, Forgot/Reset password
- Cart stored in a cookie: add, increase, decrease, remove
- Checkout form -> sends the order to a Telegram group
- Contact form -> also sends to Telegram
- Account page (shows the logged-in user)

## Notes
- Payment is simulated (the QR on checkout is a visual placeholder).
  Orders are delivered to the merchant via Telegram for manual confirmation.
- If email isn't configured, the password-reset link is printed to the
  terminal (look for "RESET LINK:") so the flow can still be tested.
