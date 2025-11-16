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
app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

if __name__ == '__main__':
    app.run(debug=True)
