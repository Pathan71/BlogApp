from flask import Flask, render_template, request, url_for, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'Secret Key'

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/blogapp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="user")
    datetime = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, email, password, role="user"):
        self.username = username
        self.email = email
        self.password = password
        self.role = role

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    images = db.Column(db.String(200), nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __init__(self, title, description, images, user_id):
        self.title = title
        self.description = description
        self.images = images
        self.user_id = user_id

with app.app_context():
    db.create_all()


# Admin Required Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first!")

            return redirect(url_for('login'))

        if session.get('role') != 'admin':
            flash("Access Denied!")
            return redirect(url_for('index'))

        return f(*args, **kwargs)

    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please Login First!")

            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


# Blog Logic
@app.route('/')
def index():
    my_blog = Blog.query.all()

    return render_template('index.html', my_blog=my_blog)

@app.route('/blogDetail/<id>')
@login_required
def blogDetail(id):
    blog = Blog.query.get(id)

    return render_template('blogDetail.html', blog=blog)

@app.route('/addBlog', methods = ['GET','POST'])
@login_required
def addBlog():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        images = request.files['image'] 

        filename = secure_filename(images.filename)
        images.save(os.path.join('static/uploads', filename))

        my_blog = Blog(
            title = title,
            description = description,
            images = filename,
            user_id = session['user_id']
        )
        db.session.add(my_blog)
        db.session.commit()

        flash("Blog Added Successfully!")

        return redirect(url_for('index'))

    return render_template("addBlog.html")

@app.route('/updateBlog/<id>', methods = ['GET', 'POST'])
@admin_required
def updateBlog(id):
    blog = Blog.query.get(id)

    blog.title = request.form['title']
    blog.description = request.form['description']
    image = request.files['image']
    if image.filename != "":
        filename = secure_filename(image.filename)
        image.save(os.path.join('static/uploads', filename))
        blog.images = filename  

    db.session.commit()
    flash("Blog Updated Successfully")

    return redirect(url_for("index"))

@app.route('/deleteBlog/<id>', methods = ['GET', 'POST'])
@admin_required
def deleteBlog(id):
    blog = Blog.query.get(id)
    db.session.delete(blog)
    db.session.commit()

    flash("Blog Deleted Successfully")

    return redirect(url_for('index'))

@app.route('/myBlog')
@login_required
def myBlog():
    if 'user_id' not in session:
        flash('Please Login First!')
        return redirect(url_for('login'))
    
    my_blog = Blog.query.filter_by(user_id=session['user_id']).all()

    return render_template('myBlog.html', my_blog=my_blog)


# User Validation Logic 
@app.route('/register', methods = ['GET', 'POST'])
def register():
    if 'user_id' in session:
        flash("You are already logged in!")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        check_email = User.query.filter_by(email=email).first()

        if check_email:
            flash("Email already exists!")
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Regsiter Successfully!")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if 'user_id' in session:
        flash("You are already logged in!")
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'admin':
                flash('Admin Login Successfully!')
            else:
                return redirect(url_for('index'))

            flash('User Login Successfully!')
            return redirect(url_for('index'))

        else:
            flash("Invalid Email or Password!")

        db.session.commit()
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logout Successfully!")

    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)