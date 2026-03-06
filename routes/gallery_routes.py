import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request, current_app
from models import Image, Device
from database import db

gallery_bp = Blueprint('gallery', __name__, url_prefix='/gallery')


@gallery_bp.route('/')
def gallery_home():
    # User must be logged in
    if 'user_id' not in session:
        flash("Please log in to view your gallery.", "warning")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    # Load only the logged-in user's images
    images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).all()

    return render_template('gallery.html', active='gallery', images=images)


@gallery_bp.route('/<int:image_id>')
def view_image(image_id):
    image = Image.query.get_or_404(image_id)

    # Prevent one user from accessing another user's image
    if 'user_id' not in session or image.user_id != session['user_id']:
        flash("You don't have permission to view this image.", "danger")
        return redirect(url_for('gallery.gallery_home'))

    return render_template('image_view.html', image=image)


# API endpoint: return list of models for a given brand
@gallery_bp.route('/api/models')
def api_models_for_brand():
    # expects ?brand=BrandName
    brand = request.args.get('brand', '').strip()
    if not brand:
        return jsonify({'error': 'brand parameter required'}), 400

    models = [d.model for d in Device.query.filter_by(brand=brand).order_by(Device.model).all()]
    return jsonify({'brand': brand, 'models': models})


# --- ADDED: Delete Image Route ---
@gallery_bp.route('/delete/<int:image_id>')
def delete_image(image_id):
    # 1. Get the image from the database
    image = Image.query.get_or_404(image_id)

    # 2. Security check: prevent deleting other people's images
    if 'user_id' not in session or image.user_id != session['user_id']:
        flash("You don't have permission to delete this image.", "danger")
        return redirect(url_for('gallery.gallery_home'))

    # 3. Delete the physical file from the 'static/uploads' folder
    try:
        # Extract just the filename from the URL path
        filename = image.file_path.split('/')[-1]
        filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)

        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error deleting file: {e}")
        # We continue even if file deletion fails, to ensure DB stays clean

    # 4. Delete the record from the database
    db.session.delete(image)
    db.session.commit()

    flash("Image deleted successfully.", "success")
    return redirect(url_for('gallery.gallery_home'))