from datetime import datetime
from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import uuid

from sqlalchemy.sql import func
from ..recommendation.recommendation_engine import get_recommendations, get_top_rated_providers
from .extensions import db

from .models import Provider, Service, User, Booking, Feedback

views = Blueprint('views', __name__)

UPLOAD_FOLDER = 'static/uploads/providers'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@views.route('/')
def home():
    return render_template("index.html")

@views.route('/about')
def about():
    return render_template("about.html")

@views.route('/services', endpoint='services')
def services_route():
    return render_template("services.html")


# ➡️ Helper function to calculate average ratings
def add_average_ratings(providers):
    for provider in providers:
        feedbacks = Feedback.query.filter_by(provider_id=provider.id).all()
        if feedbacks:
            average_rating = sum([f.rating for f in feedbacks]) / len(feedbacks)
            provider.average_rating = round(average_rating, 2)  # rounded to 2 decimal places
        else:
            provider.average_rating = 0
    return providers

@views.route('/handyman')
@login_required
def handyman():
    selected_service = request.args.get('serviceCategory')  # ❌ remove the 1 here

    # Fetch all services for dropdown
    services = Service.query.all()

    recommended_providers = []
    providers = []

    if selected_service:
        # If user selected a service, show filtered providers
        providers = Provider.query.filter_by(service_id=selected_service).all()
        providers = add_average_ratings(providers)

        if current_user.is_authenticated:
            recommended_provider_ids = get_recommendations(current_user.id, selected_service)
            recommended_providers = Provider.query.filter(Provider.id.in_(recommended_provider_ids)).all()
            recommended_providers = add_average_ratings(recommended_providers)

        if not recommended_providers:
            recommended_providers = get_top_rated_providers(selected_service)
            recommended_providers = add_average_ratings(recommended_providers)
    else:
        # When no service selected → show all providers
        providers = Provider.query.all()
        providers = add_average_ratings(providers)
        recommended_providers = []  # ❌ no recommendations if no service selected

    return render_template(
        'handyman.html',
        services=services,
        providers=providers,
        recommended_providers=recommended_providers,
        selected_service=selected_service
    )


def get_top_rated_providers(service_id):
    results = (
        db.session.query(
            Provider,
            func.avg(Feedback.rating).label('avg_rating'),
            func.count(Feedback.id).label('rating_count')
        )
        .join(Feedback, Feedback.provider_id == Provider.id)
        .filter(Provider.service_id == service_id)
        .group_by(Provider.id)
        .order_by(func.avg(Feedback.rating).desc())
        .limit(4)
        .all()
    )

    # Prepare a list of providers with extra fields
    providers = []
    for provider, avg_rating, rating_count in results:
        provider.avg_rating = round(avg_rating, 2) if avg_rating else 0
        provider.rating_count = rating_count or 0
        providers.append(provider)
    return providers


# Ensure correct path to static folder
# Ensure correct path to static folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Get project root
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'providers')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views.route('/profile-provider', methods=['GET', 'POST'])
@login_required
def provider_profile():
    provider = Provider.query.filter_by(id=current_user.id).first()

    if request.method == 'POST':
        provider.first_name = request.form.get('first_name')
        provider.last_name = request.form.get('last_name')
        provider.business_name = request.form.get('business_name')
        provider.service_id = request.form.get('service_id')
        provider.service_price = request.form.get('service_price')
        provider.experience = request.form.get('experience')
        provider.location = request.form.get('location')

        # Handle image upload
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Generate a unique filename
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"  # Unique filename
                
                # Delete old image if it exists
                if provider.image:
                    old_image_path = os.path.join(UPLOAD_FOLDER, provider.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                # Save the new file
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                
                # Store only the filename in DB
                provider.image = filename  

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('views.provider_profile'))

    services = Service.query.all()  # Get all services for dropdown
    return render_template('provider_profile.html', provider=provider, services=services)


@views.route('/submit_feedback', methods=['GET', 'POST'])
@login_required
def submit_feedback():
    booking_id = request.args.get('booking_id')

    if not booking_id:
        flash("Invalid booking ID!", "danger")
        return redirect(url_for("views.booking_history"))

    # Fetch the booking details to get the provider_id
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first()
    if not booking:
        flash("Booking not found!", "danger")
        return redirect(url_for("views.booking_history"))

    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')

        if not rating:
            flash("Rating is required!", "danger")
            return redirect(url_for("views.submit_feedback", booking_id=booking_id))

        # Ensure provider_id is included
        feedback = Feedback(
            booking_id=booking_id,
            provider_id=booking.provider_id,  # Fetch provider_id from the booking
            rating=rating,
            comment=comment,
            user_id=current_user.id
        )

        db.session.add(feedback)
        db.session.commit()

        flash("Feedback submitted successfully!", "success")
        return redirect(url_for("views.booking_history"))

    return render_template("submit_feedback.html", booking_id=booking_id)



@views.route('/profile-customer', methods=['GET', 'POST'])
@login_required
def customer_profile():
    if request.method == 'POST':
        # Update Profile Fields
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        current_user.address = request.form.get('address')

        # Handle Profile Picture Upload
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Generate a unique filename
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"  # Unique filename
                
                # Delete old image if it exists
                if current_user.image and current_user.image != "default.png":
                    old_image_path = os.path.join(UPLOAD_FOLDER, current_user.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                # Save the new file
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)

                # Store only the filename in DB
                current_user.image = filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('views.customer_profile'))  # Fix function reference

    return render_template('customer_profile.html', user=current_user)

@views.route('/provider/<int:provider_id>', methods=['GET'])
@login_required
def provider_details(provider_id):
    provider = Provider.query.get_or_404(provider_id)
    return render_template('provider_details.html', provider=provider)

@views.route('/book/<int:provider_id>', methods=['GET','POST'])
@login_required
def book_provider(provider_id):
    provider = Provider.query.get_or_404(provider_id)
    booking_date = request.form.get('booking_date')
    booking_time = request.form.get('booking_time')

    if not booking_date or not booking_time:
        flash("Please select both date and time.", "danger")
        return redirect(url_for('views.provider_details', provider_id=provider.id))

    # Save to database
    new_booking = Booking(
        customer_id=current_user.id,
        provider_id=provider.id,
        service_id=provider.service_id,
        booking_date=datetime.strptime(booking_date, "%Y-%m-%d"),
        booking_time=datetime.strptime(booking_time, "%H:%M").time(),
        status="Pending"
    )

    db.session.add(new_booking)
    db.session.commit()
    print("Booking successful! Your request is pending confirmation.")
    
    flash("Booking successful! Your request is pending confirmation.", "success")
    return redirect(url_for('views.booking_history'))


@views.route('/booking-history')
@login_required
def booking_history():
    bookings = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.created_at.desc()).all()
    
    # Create a dictionary to store feedback status for each booking
    feedback_status = {booking.id: Feedback.query.filter_by(booking_id=booking.id).first() is not None for booking in bookings}

    return render_template('booking_history.html', bookings=bookings, feedback_status=feedback_status)

@views.route('/cancel-booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.customer_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('booking_history'))

    if booking.status == 'Pending':
        booking.status = 'Cancelled'
        db.session.commit()
        flash('Booking has been cancelled successfully.', 'success')
    else:
        flash('Booking cannot be cancelled.', 'warning')

    return redirect(url_for('views.booking_history'))


@views.route('/provider-bookings')
@login_required
def provider_bookings():

    bookings = Booking.query.filter_by(provider_id=current_user.id).order_by(Booking.created_at.desc()).all()
    
    return render_template('provider_bookings.html', bookings=bookings)


@views.route('/confirm-booking/<int:booking_id>', methods=['POST'])
@login_required
def confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # Check if provider owns the booking
    if booking.provider_id != current_user.id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('views.provider_bookings'))

    if booking.status == "Pending":
        booking.status = "Confirmed"
        db.session.commit()
        flash("Booking confirmed successfully!", "success")
    else:
        flash("Only pending bookings can be confirmed.", "warning")

    return redirect(url_for('views.provider_bookings'))


@views.route('/reject-booking/<int:booking_id>', methods=['POST'])
@login_required
def reject_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # Check if provider owns the booking
    if booking.provider_id != current_user.id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('views.provider_bookings'))

    if booking.status == "Pending":
        booking.status = "Rejected"
        db.session.commit()
        flash("Booking rejected successfully!", "success")
    else:
        flash("Only pending bookings can be rejected.", "warning")

    return redirect(url_for('views.provider_bookings'))


@views.route('/complete-booking/<int:booking_id>', methods=['POST'])
@login_required
def complete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # Check if the provider owns this booking
    if booking.provider_id != current_user.id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('views.provider_bookings'))

    if booking.status == "Confirmed":
        booking.status = "Completed"
        db.session.commit()
        flash("Booking marked as completed!", "success")
    else:
        flash("Only confirmed bookings can be marked as completed.", "warning")

    return redirect(url_for('views.provider_bookings'))

from HandyHub.Handy.models import ContactMessage  # import your ContactMessage model

@views.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        full_name = request.form.get('name')  # ✅ store in full_name (not name)
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not full_name or not email or not message:
            flash('Please fill all required fields.', 'danger')
        else:
            new_message = ContactMessage(
                full_name=full_name,  # ✅ pass full_name (NOT name)
                email=email,
                subject=subject,
                message=message
            )
            db.session.add(new_message)
            db.session.commit()
            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('views.contact'))  # ✅ small fix: 'views.contact'
    return render_template('contact.html')
@views.route('/customer-forget-password', methods=['GET', 'POST'])
def customer_forget_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')

        user = User.query.filter_by(email=email, role='customer').first()

        if user:
            user.set_password(new_password)  # calling your model's set_password function
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('auth.customer_login'))  # your login page route
        else:
            flash('Email not found!', 'danger')
            return redirect(url_for('views.customer_forget_password'))

    return render_template('customer-forget-password.html')

@views.route('/provider-forget-password', methods=['GET', 'POST'])
def provider_forget_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')

        provider = Provider.query.filter_by(email=email).first()

        if provider:
            provider.set_password(new_password)   # Assuming your Provider model also has set_password method
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('auth.provider_login'))
        else:
            flash('Provider not found with this email.', 'danger')
            return redirect(url_for('views.provider_forget_password'))

    return render_template('provider-forget-password.html')

@views.route('/terms_of_service')
def terms_of_service():
    return render_template('terms_of_service.html')

@views.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

