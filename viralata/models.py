#!/usr/bin/env python
# coding: utf-8

from passlib.apps import custom_app_context as pwd_context
# from sqlalchemy import Column, String, Integer, Boolean
# from sqlalchemy.ext.declarative import declarative_base

from extensions import db


# Base = declarative_base()


# class User(Base):
class User(db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True)
    password_hash = db.Column(db.String(128), nullable=True)
    # name = db.Column(db.String(100))
    email = db.Column(db.String(200), default='')
    active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(500))
    last_token_exp = db.Column(db.Integer, nullable=True)

    def is_active(self):
        return self.active

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    @classmethod
    def get_user(cls, username):
        return (db.session.query(cls)
                .filter(cls.username == username).one())

    @classmethod
    def verify_user_password(cls, username, password):
        return cls.get_user(username).verify_password(password)
