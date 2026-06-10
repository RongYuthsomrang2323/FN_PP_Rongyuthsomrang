from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, make_response
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from product import (
    products as pro,
    get_product_by_category,
    get_product_by_title,
    get_product_by_id,
)
import secrets
import json
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'your-secret-key'

# Mail config — replace with your Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'panqniceone4@gmail.com'
app.config['MAIL_PASSWORD'] = 'jecvtjuoohcddfou'

# Telegram config — replace with your bot token + group chat id
TELEGRAM_TOKEN = '8649196302:AAH2sY6Q-74VBN37ieZA5uEig4-ZKiOno4k'
TELEGRAM_CHAT_ID = '-5105045764'

db = SQLAlchemy(app)
mail = Mail(app)

reset_tokens = {}  # { token: user_id }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))


with app.app_context():
    db.create_all()


# ──────────────────────────────────────────────
#  CART  (stored in a cookie as JSON: { "product_id": qty })
# ──────────────────────────────────────────────
def read_cart():
    raw = request.cookies.get('cart')
    return json.loads(raw) if raw else {}


def build_cart_items(cart):
    """Turn the {id: qty} cookie into full line items + subtotal + count."""
    items, subtotal, count = [], 0, 0
    for pid, qty in cart.items():
        p = get_product_by_id(pid)
        if p:
            line = p['price'] * qty
            subtotal += line
            count += qty
            items.append({'product': p, 'qty': qty, 'line_total': round(line, 2)})
    return items, round(subtotal, 2), count


@app.post('/cart/add/<int:product_id>')
def cart_add(product_id):
    cart = read_cart()
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    resp = make_response(redirect(request.referrer or url_for('cart')))
    resp.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return resp


@app.post('/cart/update/<int:product_id>/<action>')  # action = inc / dec / remove
def cart_update(product_id, action):
    cart = read_cart()
    key = str(product_id)
    if action == 'inc':
        cart[key] = cart.get(key, 0) + 1
    elif action == 'dec':
        cart[key] = cart.get(key, 1) - 1
        if cart[key] <= 0:
            cart.pop(key, None)
    elif action == 'remove':
        cart.pop(key, None)
    resp = make_response(redirect(url_for('cart')))
    resp.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return resp


@app.get('/cart')
def cart():
    items, subtotal, count = build_cart_items(read_cart())
    return render_template('front/cart.html', items=items, subtotal=subtotal, count=count)


# ──────────────────────────────────────────────
#  CHECKOUT  →  sends order to Telegram group
# ──────────────────────────────────────────────
@app.get('/checkout')
def checkout():
    items, subtotal, count = build_cart_items(read_cart())
    return render_template('front/checkout.html', items=items, subtotal=subtotal, count=count)


@app.post('/checkout')
def place_order():
    cart = read_cart()
    items, subtotal, count = build_cart_items(cart)

    if not items:
        flash('Your cart is empty.')
        return redirect(url_for('cart'))

    first_name = request.form.get('first_name', '')
    last_name = request.form.get('last_name', '')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    name = f"{first_name} {last_name}".strip()

    # Build the Telegram message
    lines = [f"- {it['product']['title']} x{it['qty']} = ${it['line_total']:.2f}" for it in items]
    message = (
        "🛒 *New Order*\n\n"
        f"👤 {name}\n"
        f"✉️ {email}\n"
        f"📞 {phone}\n"
        f"📍 {address}\n\n"
        "*Items:*\n" + "\n".join(lines) + "\n\n"
        f"*Total: ${subtotal:.2f}*"
    )

    # Send to Telegram (won't crash the order if it fails)
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10,
        )
    except requests.RequestException as e:
        print("Telegram send failed:", e)

    # Clear the cart cookie and show a success page
    resp = make_response(render_template('front/checkout.html', ordered=True))
    resp.set_cookie('cart', '', expires=0)
    return resp


# ──────────────────────────────────────────────
#  ACCOUNT  (requires login)
# ──────────────────────────────────────────────
@app.get('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('front/account.html', user=user)


# ──────────────────────────────────────────────
#  CONTACT
# ──────────────────────────────────────────────
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        body = request.form.get('message', '')

        message = (
            "📨 *New Contact Message*\n\n"
            f"👤 {name}\n"
            f"✉️ {email}\n\n"
            f"{body}"
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'},
                timeout=10,
            )
        except requests.RequestException as e:
            print("Telegram send failed:", e)

        flash('Thanks! Your message has been sent.')
        return redirect(url_for('contact'))

    return render_template('front/contact.html')


# ──────────────────────────────────────────────
#  AUTH  (register / login / logout / reset)
# ──────────────────────────────────────────────
@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        name = f"{first_name} {last_name}"
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash('Passwords do not match')
            return render_template('front/create-user.html')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered')
            return render_template('front/create-user.html')

        hashed = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('front/create-user.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('home'))
        flash('Invalid email or password')
    return render_template('front/login.html')


@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(16)
            reset_tokens[token] = user.id
            link = url_for('reset_password', token=token, _external=True)
            try:
                msg = Message(
                    subject='Reset Your Password',
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[email]
                )
                msg.body = f'Hello {user.name},\n\nReset your password:\n\n{link}'
                mail.send(msg)
            except Exception as e:
                print("Email send failed:", e)
                print("RESET LINK:", link)
        # Always show this message — don't reveal if the email exists
        flash('If that email is registered, a reset link has been sent.')
    return render_template('front/forgot-password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = reset_tokens.get(token)
    if not user_id:
        flash('Invalid or expired reset link.')
        return redirect(url_for('forget_password'))
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match')
            return render_template('front/reset-password.html', token=token)
        user = User.query.get(user_id)
        user.password = generate_password_hash(password)
        db.session.commit()
        del reset_tokens[token]
        flash('Password updated! Please login.')
        return redirect(url_for('login'))
    return render_template('front/reset-password.html', token=token)


# ──────────────────────────────────────────────
#  STOREFRONT  (home / products / product)
# ──────────────────────────────────────────────
@app.get('/')
def home():
    return render_template('front/index.html', products=pro)


@app.get('/products')
def products():
    return render_template('front/products.html', products=pro)


@app.get('/product/<product_name>')
def product(product_name):
    product = get_product_by_title(product_name)
    related_product = get_product_by_category(product['category'])
    return render_template('front/product.html', product=product, related_product=related_product)


if __name__ == '__main__':
    app.run(debug=True)

