from flask import Blueprint, render_template, session, redirect, url_for, flash
from models import Image

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
