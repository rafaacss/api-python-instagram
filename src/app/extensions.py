from flask_cors import CORS

def init_extensions(app):
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Warmup-Token"],
            "expose_headers": ["Content-Range", "Accept-Ranges", "Content-Length"]
        }
    })