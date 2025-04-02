from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Regexp
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from datetime import datetime
import csv
from io import StringIO
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///members.db'
db = SQLAlchemy(app)

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenoms = db.Column(db.String(100), nullable=False)
    promo = db.Column(db.Integer, nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    ville_residence = db.Column(db.String(100), nullable=False)
    pays_residence = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class MemberForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    prenoms = StringField('Prénoms', validators=[DataRequired(), Length(min=2, max=100)])
    promo = IntegerField('Promotion', validators=[DataRequired(), NumberRange(min=1994, max=2027, message='La promotion doit être comprise entre 1994 et 2027')])
    telephone = StringField('Numéro de téléphone', validators=[DataRequired(), Length(min=8, max=20), Regexp('^[0-9]+$', message='Le numéro de téléphone doit contenir uniquement des chiffres')])
    email = StringField('Email', validators=[DataRequired(), Email()])
    ville_residence = StringField('Ville de résidence', validators=[DataRequired(), Length(min=2, max=100)])
    pays_residence = StringField('Pays de résidence', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Enregistrer')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = MemberForm()
    if form.validate_on_submit():
        # Vérifier si l'email existe déjà
        existing_member = Member.query.filter_by(email=form.email.data).first()
        if existing_member:
            flash('Un membre avec cet email existe déjà. Veuillez utiliser un autre email ou modifier les informations existantes via la recherche.', 'error')
            return render_template('register.html', form=form)

        member = Member(
            nom=form.nom.data,
            prenoms=form.prenoms.data,
            promo=form.promo.data,
            telephone=form.telephone.data,
            email=form.email.data,
            ville_residence=form.ville_residence.data,
            pays_residence=form.pays_residence.data
        )
        try:
            db.session.add(member)
            db.session.commit()
            flash('Inscription réussie!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue lors de l\'enregistrement. Veuillez réessayer.', 'error')
    return render_template('register.html', form=form)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        email = request.form.get('email')
        member = Member.query.filter_by(email=email).first()
        return render_template('search.html', member=member)
    return render_template('search.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
    
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    members = Member.query.order_by(Member.nom).all()
    return render_template('admin.html', members=members)

@app.route('/export-csv')
@login_required
def export_csv():
    members = Member.query.order_by(Member.nom).all()
    
    # Créer un buffer pour le CSV
    si = StringIO()
    cw = csv.writer(si, delimiter=';')
    
    # Écrire l'en-tête
    cw.writerow(['Nom', 'Prénoms', 'Promotion', 'Téléphone', 'Email', 'Ville de résidence', 'Pays de résidence'])
    
    # Écrire les données
    for member in members:
        cw.writerow([
            member.nom,
            member.prenoms,
            member.promo,
            member.telephone,
            member.email,
            member.ville_residence,
            member.pays_residence
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=membres_mis.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    return output

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    member = Member.query.get_or_404(id)
    form = MemberForm(obj=member)
    if form.validate_on_submit():
        member.nom = form.nom.data
        member.prenoms = form.prenoms.data
        member.promo = form.promo.data
        member.telephone = form.telephone.data
        member.email = form.email.data
        member.ville_residence = form.ville_residence.data
        member.pays_residence = form.pays_residence.data
        try:
            db.session.commit()
            flash('Informations mises à jour avec succès!', 'success')
            return redirect(url_for('search'))
        except:
            db.session.rollback()
            flash('Une erreur est survenue lors de la mise à jour.', 'error')
    return render_template('edit.html', form=form, member=member)

@app.cli.command('create-admin')
def create_admin():
    """Créer un nouvel administrateur"""
    username = input('Nom d\'utilisateur: ')
    password = input('Mot de passe: ')
    
    admin = Admin(username=username)
    admin.set_password(password)
    
    with app.app_context():
        db.session.add(admin)
        db.session.commit()
        print(f'Administrateur {username} créé avec succès!')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5009)
