from flask import Flask, render_template
from src.api.polygons import bp as polygons_bp


def create_app():
    app = Flask(__name__, template_folder='src/web/templates', static_folder='src/web/static')
    app.register_blueprint(polygons_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')
