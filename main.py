# from diffusers import StableDiffusionPipeline
# import torch
#
# pipe = StableDiffusionPipeline.from_pretrained('runwayml/stable-diffusion-v1-5')
# pipe = pipe.to('cpu')
#
# prompt = 'dark gothic desktop background'
# image = pipe(prompt).images[0]
# image.save('output.png')

from flask import Flask, render_template
from config import Config
from database import db
from routes.auth_routes import auth_bp
from routes.gallery_routes import gallery_bp

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database with app
db.init_app(app)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(gallery_bp, url_prefix='/gallery')

# Optional: basic homepage route
@app.route('/')
def index():
    return render_template('index.html', active='index')


if __name__ == '__main__':
    app.run(debug=True)
