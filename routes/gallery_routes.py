from flask import Blueprint, render_template

gallery_bp = Blueprint('gallery', __name__, url_prefix='/gallery')


@gallery_bp.route('/')
def gallery_home():
    # Later: fetch images from DB
    return render_template('gallery.html', active='gallery')


@gallery_bp.route('/<int:image_id>')
def view_image(image_id):
    # Later: fetch specific image from DB
    return render_template('image_view.html', image_id=image_id)
