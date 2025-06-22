import pprint
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash
from .models import User, Provider
from . import db  
from werkzeug.security import check_password_hash
from flask import session


auth = Blueprint('auth', __name__)

# ======================= Customer Authentication ======================= #

@auth.route('/customer-login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if customer exists in the database
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with this email.', category='error')
            return redirect(url_for('auth.customer_login'))

        # Verify password
        if not user.check_password(password):
            flash('Incorrect password. Please try again.', category='error')
            return redirect(url_for('auth.customer_login'))

        # If authentication is successful, log in the user
        login_user(user, remember=True)
        session['user_type'] = 'customer'  # Store user type in session

        # flash('Login successful!', category='success')
        return redirect(url_for('views.home'))  # Redirect to customer dashboard

    return render_template("customer_login.html")



@auth.route('/customer-signup', methods=['GET', 'POST'])
def customer_signup():
    if request.method == 'POST':
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address', 'Not Provided')
        role = request.form.get('role', 'customer')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')

        print("Received Data:", first_name, last_name, email, phone, address, password, confirm_password)

        # Check if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        existing_phone = User.query.filter_by(phone=phone).first()

        if existing_user:
            flash('<div class="alert alert-danger" role="alert">Email already exists.</div>', category='error')
            print("User already exists!")
            return redirect(url_for('auth.customer_signup'))
        if existing_phone:
            flash('<div class="alert alert-danger" role="alert">Phone number already exists.</div>', category='error')
            return redirect(url_for('auth.customer_signup'))

        # Check if passwords match
        if password != confirm_password:
            flash('<div class="alert alert-danger" role="alert">Passwords do not match!</div>', category='error')
            print("Passwords do not match!")
            return redirect(url_for('auth.customer_signup'))

        # Create new user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            role=role  # Store address
        )

        # Ensure password hashing method is available
        if hasattr(new_user, 'set_password'):
            new_user.set_password(password)  # Hash password before storing
        else:
            flash('<div class="alert alert-danger" role="alert">Error: User model does not have a password hashing method.</div>', category='error')
            return redirect(url_for('auth.customer_signup'))

        db.session.add(new_user)
        db.session.commit()
        print("User created successfully!")

        # Log in the new user
        login_user(new_user, remember=True)
        # flash('<div class="alert alert-success" role="alert">Customer account created successfully!</div>', category='success')
        return redirect(url_for('views.home'))

    return render_template("customer_register.html", user=current_user)

# ======================= Provider Authentication ======================= #

@auth.route('/provider-login', methods=['GET', 'POST'])
def provider_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if provider exists in the database
        provider = Provider.query.filter_by(email=email).first()

        if not provider:
            flash('No account found with this email.', category='error')
            return redirect(url_for('auth.provider_login'))

        # Verify password
        if not check_password_hash(provider.password_hash, password):
            flash('Incorrect password. Please try again.', category='error')
            return redirect(url_for('auth.provider_login'))

        # If authentication is successful, log in the provider
        login_user(provider, remember=True)
        session['user_type'] = 'provider'  # Store user type in session

        # flash('Login successful!', category='success')
        return redirect(url_for('views.home'))  # Redirect to provider dashboard

    return render_template("provider_login.html")


@auth.route('/provider-signup', methods=['GET', 'POST'])
def provider_signup():
    from .models import Service  # Ensure you import the Service model

    # Fetch all available services from the database
    services = Service.query.all()

    if request.method == 'POST':
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        business_name = request.form.get('businessName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role', 'provider')
        service_id = request.form.get('serviceCategory')  # Gets service ID
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')

        # Check if the email already exists
        existing_provider_email = Provider.query.filter_by(email=email).first()
        if existing_provider_email:
            flash('<div class="alert alert-danger" role="alert">Email already exists.</div>', category='error')
            return redirect(url_for('auth.provider_signup'))

        # Check if the phone already exists
        existing_provider_phone = Provider.query.filter_by(phone=phone).first()
        if existing_provider_phone:
            flash('<div class="alert alert-danger" role="alert">Phone number already exists.</div>', category='error')
            return redirect(url_for('auth.provider_signup'))

        # Check if passwords match
        if password != confirm_password:
            flash('<div class="alert alert-danger" role="alert">Passwords do not match.</div>', category='error')
            return redirect(url_for('auth.provider_signup'))

        # Ensure the service ID exists
        service = Service.query.get(service_id)
        if not service:
            flash('<div class="alert alert-danger" role="alert">Invalid service selected.</div>', category='error')
            return redirect(url_for('auth.provider_signup'))

        # Create new provider
        new_provider = Provider(
            first_name=first_name,
            last_name=last_name,
            business_name=business_name,
            email=email,
            phone=phone,
            service_id=service.id,  # Assigning service ID
            role=role,
        )
        
        # Ensure password hashing method is available
        if hasattr(new_provider, 'set_password'):
            new_provider.set_password(password)  # Hash password before storing
        else:
            flash('<div class="alert alert-danger" role="alert">Error: Provider model does not have a password hashing method.</div>', category='error')
            return redirect(url_for('auth.provider_signup'))

        # Save to DB
        db.session.add(new_provider)
        db.session.commit()

        # Log in the provider
        login_user(new_provider, remember=True)
        # flash('<div class="alert alert-success" role="alert">Provider account created successfully!</div>', category='success')
        return redirect(url_for('views.home'))

    # Pass services list to the template
    return render_template("provider_register.html", user=current_user, services=services)

@auth.route('/logout')
@login_required
def logout():
    # pprint.pprint(dict(session))
    logout_user()
    
    # flash('You have been logged out.', category='info')a
    return redirect(url_for('views.home'))