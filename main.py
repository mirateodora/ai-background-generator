import os
import uuid
import textwrap
from PIL import Image as PILImage, ImageFilter, ImageDraw, ImageFont, ImageOps
from flask import Flask, render_template, request, session, redirect, url_for, flash
from config import Config
from database import db
from routes.auth_routes import auth_bp
from routes.gallery_routes import gallery_bp
from models import Device, Image, Quote, ThemePrompt

# --- Import the Hugging Face Client ---
from huggingface_hub import InferenceClient

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database with app
db.init_app(app)

# Initialize the Hugging Face Cloud API using your hidden PyCharm variable
print("Connecting to Hugging Face API...")
hf_token = app.config.get('HF_TOKEN')
if not hf_token:
    print("WARNING: HF_TOKEN environment variable is missing!")

client = InferenceClient(model="stabilityai/stable-diffusion-xl-base-1.0", token=hf_token)
print("Connected!")

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

    if quote_checked == 'on' and not quote_text:
        # db.func.random() randomly shuffles the table, and .first() grabs the top one!
        random_quote = Quote.query.order_by(db.func.random()).first()

        if random_quote:
            quote_text = random_quote.text
        else:
            # A tiny safety net just in case the database table is ever empty
            quote_text = "Keep going."

    # Get target resolution from database
    target_device = Device.query.filter_by(brand=brand, model=model).first()
    if not target_device:
        flash("Error: Device not found.", "danger")
        return redirect(url_for('index'))

    random_prompt_obj = ThemePrompt.query.filter_by(theme=theme).order_by(db.func.random()).first()

    if random_prompt_obj:
        prompt = random_prompt_obj.prompt_text
    else:
        # Fallback just in case a theme is missing from the database
        prompt = f"Beautiful {theme} background wallpaper for phone, masterpiece, stunning digital art, highly detailed, 4k resolution"
    print(f"Sending request to Hugging Face Cloud: '{prompt}'...")
    try:
        # The API instantly returns a Pillow image!
        base_image = client.text_to_image(prompt)
    except Exception as e:
        print(f"API Error: {e}")
        flash("The AI is currently busy or warming up. Please try again in 30 seconds!", "danger")
        return redirect(url_for('index'))

    # --- STEP 2: Crop to desired size ---
    target_size = (target_device.width, target_device.height)
    final_image = ImageOps.fit(base_image, target_size, PILImage.Resampling.LANCZOS)

    # --- STEP 3: Apply blur if needed ---
    if blur_effect == 'on':
        final_image = final_image.filter(ImageFilter.GaussianBlur(radius=5))

    # --- STEP 4: Write the quote (with wrapping & custom font) ---
    if quote_checked == 'on' and quote_text:
        draw = ImageDraw.Draw(final_image)

        # Load your downloaded font
        font_path = os.path.join(app.root_path, 'static', 'fonts', 'CalSans-Regular.ttf')
        try:
            font = ImageFont.truetype(font_path, size=80)
        except IOError:
            print(f"WARNING: Could not find font at {font_path}! Falling back to default font.")
            font = ImageFont.load_default()

        # Wrap the text to fit the screen (approx 18 characters per line for size 80 font)
        lines = textwrap.wrap(quote_text, width=18)

        # Calculate heights
        line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line
                        in lines]
        line_spacing = 15
        total_text_height = sum(line_heights) + (line_spacing * (len(lines) - 1))

        # Find starting Y coordinate
        y = (target_device.height - total_text_height) / 2
        shadow_offset = 4

        # Draw text
        for i, line in enumerate(lines):
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            text_width = right - left
            x = (target_device.width - text_width) / 2

            # Shadow
            draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill="black")
            # White text
            draw.text((x, y), line, font=font, fill="white")

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