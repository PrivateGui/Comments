from diffusers import DiffusionPipeline
from flask import Flask, send_file

app = Flask(__name__)

@app.route("/")
def generate_and_serve():
    pipe = DiffusionPipeline.from_pretrained("Wan-AI/Wan2.1-T2V-1.3B-Diffusers")
    prompt = "Astronaut in a jungle, cold color palette, muted colors, detailed, 8k"
    image = pipe(prompt).images[0]
    image.save("output.png")
    return send_file("output.png", mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
