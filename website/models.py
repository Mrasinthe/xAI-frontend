from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from flask_marshmallow import Marshmallow


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
        # self.notes = notes

    # class userSChema(ma.Schema):
    #     class Meta:
    #         fields = ('email', 'password', 'first_name', 'user_role', 'date')

    # user_schema = userSChema()
    # user_schemas = userSChema(many=True)
