from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_login import UserMixin
from sqlalchemy.sql import func
from flask_marshmallow import Marshmallow


db = SQLAlchemy()

DB_NAME = "spatial"
# DB_NAME = "database.db"


def create_app():

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'ssss ssss'
    # app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config[
        'SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:postgres@localhost:5432/{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_SIZE'] = 2000000
    db = SQLAlchemy(app)
    ma = Marshmallow(app)
    db.init_app(app)

    # app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:postgres@localhost:5432/{DB_NAME}'
    # db = SQLAlchemy(app)

    class DataModel(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        data = db.Column(db.String(10000))
        model = db.Column(db.LargeBinary)
        date = db.Column(db.DateTime(timezone=True), default=func.now())
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

        def __init__(self, data, model, user_id):
            self.data = data
            self.model = model
            self.user_id = user_id

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(150), unique=True, nullable=False)
        password = db.Column(db.String(150), nullable=False)
        first_name = db.Column(db.String(150), unique=True, nullable=False)
        user_role = db.Column(db.String(150), unique=True, nullable=False)
        date = db.Column(db.DateTime(timezone=True), default=func.now())
        # notes = db.relationship('DataModel')

        def __init__(self, email, password, first_name, user_role, date):
            self.email = email
            self.password = password
            self.first_name = first_name
            self.user_role = user_role
            self.date = date

    class userSChema(ma.Schema):
        class Meta:
            fields = ('email', 'password', 'first_name', 'user_role', 'date')

    user_schema = userSChema()
    user_schemas = userSChema(many=True)

    @app.route('/get_users', methods=['GET'])
    # @login_required
    async def users_details():
        all_users = User.query.all()
        results = user_schemas.dump(all_users)
        return jsonify(results)

    @app.route('/get_user/<id>', methods=['GET'])
    # @login_required
    async def user_details(id):
        all_users = User.query.get(id)
        return user_schema.jsonify(all_users)

    from .views import views
    from .auth import auth
    from .models import User, DataModel

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')
