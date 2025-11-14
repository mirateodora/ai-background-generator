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

if __name__ == '__main__':
    app.run(debug=True)
