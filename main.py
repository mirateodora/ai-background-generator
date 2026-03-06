
from diffusers import StableDiffusionPipeline
import os
import uuid
from PIL import Image as PILImage, ImageFilter, ImageDraw, ImageFont, ImageOps
from flask import Flask, render_template, request, session, redirect, url_for, flash
from config import Config
from database import db
from routes.auth_routes import auth_bp
from routes.gallery_routes import gallery_bp
from models import Device, Image  # <-- Added Image here
import textwrap

# ... (Keep your diffusers setup here) ...

print("Loading Stable Diffusion model... (This might take a minute)")
pipe = StableDiffusionPipeline.from_pretrained('runwayml/stable-diffusion-v1-5')
pipe = pipe.to('cpu') # Uses CPU, which is slower but works without a dedicated GPU
print("Model loaded successfully!")
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
    # Query devices to populate brand/model dropdowns
    try:
        devices = Device.query.all()
        brands = sorted({d.brand for d in devices})
        models_by_brand = {}
        for d in devices:
            models_by_brand.setdefault(d.brand, set()).add(d.model)
        # convert sets to sorted lists for consistent ordering
        models_by_brand = {b: sorted(list(models_by_brand.get(b, []))) for b in brands}
    except Exception:
        # If DB isn't available or has no entries, fall back to empty lists
        brands = []
        models_by_brand = {}

    # Themes: keep as a simple list here (could be a DB table in the future)
    themes = [
        'Abstract', 'Nature', 'Minimal', 'Dark', 'Light', 'Space', 'Retro'
    ]


    return render_template('index.html', active='index', brands=brands, models_by_brand=models_by_brand, themes=themes)


import textwrap  # Add this to your imports at the top of main.py if you haven't already


@app.route('/generate', methods=['POST'])
def generate():
    # Security check: Make sure the user is logged in
    if 'user_id' not in session:
        flash("Please log in to generate wallpapers.", "warning")
        return redirect(url_for('auth.login'))

    # Extract form data
    brand = request.form.get('brand')
    model = request.form.get('model')
    theme = request.form.get('theme')
    quote_checked = request.form.get('quote')
    quote_text = request.form.get('quoteText')
    blur_effect = request.form.get('blurEffect')

    # Get target resolution from database
    target_device = Device.query.filter_by(brand=brand, model=model).first()
    if not target_device:
        flash("Error: Device not found.", "danger")
        return redirect(url_for('index'))

    # --- STEP 1: Generate the base image (with aesthetic prompts) ---
    prompt = f"Beautiful {theme} background wallpaper for phone, masterpiece, stunning digital art, highly detailed, vibrant colors, 4k resolution, trending on artstation"
    negative_prompt = "ugly, blurry, bad anatomy, text, watermark, signature, cropped, low resolution, grainy, noisy"

    print(f"Generating aesthetic image: '{prompt}'...")
    # num_inference_steps=35 gives a good balance of quality and generation speed
    base_image = pipe(prompt, negative_prompt=negative_prompt, num_inference_steps=35).images[0]

    # --- STEP 2: Crop to desired size ---
    target_size = (target_device.width, target_device.height)
    final_image = ImageOps.fit(base_image, target_size, PILImage.Resampling.LANCZOS)

    # --- STEP 3: Apply blur if needed ---
    if blur_effect == 'on':
        final_image = final_image.filter(ImageFilter.GaussianBlur(radius=5))

    # --- STEP 4: Write the quote (with wrapping & custom font) ---
    if quote_checked == 'on' and quote_text:
        draw = ImageDraw.Draw(final_image)

        # Load your downloaded font (Make sure this filename matches exactly!)
        font_path = os.path.join(app.root_path, 'static', 'fonts', 'CalSans-Regular.ttf')
        try:
            font = ImageFont.truetype(font_path, size=80)
        except IOError:
            print(f"WARNING: Could not find font at {font_path}! Falling back to default font.")
            font = ImageFont.load_default()

        # Wrap the text to fit the screen (approx 18 characters per line for size 80 font)
        lines = textwrap.wrap(quote_text, width=18)

        # Calculate the height of each line to find the total text block height
        line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line
                        in lines]
        line_spacing = 15
        total_text_height = sum(line_heights) + (line_spacing * (len(lines) - 1))

        # Find the starting Y coordinate to center the whole block of text vertically
        y = (target_device.height - total_text_height) / 2

        shadow_offset = 4

        # Draw each line individually, centered horizontally
        for i, line in enumerate(lines):
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            text_width = right - left
            x = (target_device.width - text_width) / 2

            # Draw shadow
            draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill="black")

            # Draw white text
            draw.text((x, y), line, font=font, fill="white")

            # Move down for the next line
            y += line_heights[i] + line_spacing

    # --- STEP 5: Save File & Update Database ---
    upload_dir = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(upload_dir, filename)
    final_image.save(filepath)

    new_image = Image(
        user_id=session['user_id'],
        device_id=target_device.id,
        title=f"{theme} Wallpaper",
        file_path=url_for('static', filename=f'uploads/{filename}')
    )
    db.session.add(new_image)
    db.session.commit()

    flash("Wallpaper generated successfully!", "success")
    return redirect(url_for('gallery.gallery_home'))

if __name__ == '__main__':
    app.run(debug=True)
