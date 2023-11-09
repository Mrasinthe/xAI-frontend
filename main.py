# Flask API
from website import create_app, create_database
from flask import Blueprint, render_template
from flask_login import login_required, current_user
import datetime

# Calling Flask API
flask_app = create_app()


views = Blueprint('views', __name__)


@flask_app.get('/')
def home():
    return render_template("home.html", user=current_user)


if __name__ == '__main__':
    create_database(flask_app)
    flask_app.run(debug=True)
