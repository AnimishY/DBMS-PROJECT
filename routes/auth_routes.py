from flask import Blueprint, session, redirect, url_for, render_template, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from config.database import connect_to_mysql

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/signup/buyer')
def signup_buyer():
    return redirect(url_for('buyer.register'))

@auth_blueprint.route('/signup/seller')
def signup_seller():
    return redirect(url_for('seller.register'))

@auth_blueprint.route('/signin/buyer')
def signin_buyer():
    return redirect(url_for('buyer.login'))

@auth_blueprint.route('/signin/seller')
def signin_seller():
    return redirect(url_for('seller.login'))

@auth_blueprint.route('/logout')
def logout():
    if 'buyer_id' in session:
        return redirect(url_for('buyer.logout'))
    elif 'seller_id' in session:
        return redirect(url_for('seller.logout'))
    return redirect(url_for('home'))