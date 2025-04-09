from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify
from urllib.parse import urlparse
import requests
import jwt
from time import time, sleep
from flask_mail import Mail, Message
import os

import pycountry

# Liste des pays en français avec leurs noms en anglais
COUNTRIES = sorted([country.name for country in pycountry.countries])
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, PasswordField, TextAreaField, SelectField, BooleanField, FloatField, DateTimeField, DateField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Regexp, EqualTo, Optional, URL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from datetime import datetime
import csv
from io import StringIO
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/hardysmile/CascadeProjects/mis_association/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiser SQLAlchemy avec l'application
db = SQLAlchemy()
db.init_app(app)

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

# Configuration de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'votre-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'votre-mot-de-passe')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'votre-email@gmail.com')

# Initialiser Flask-Mail
mail = Mail(app)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # afterwork, conference, formation, etc.
    max_participants = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    meeting_link = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, ongoing, completed, cancelled
    
    # Relations
    participants = db.relationship('Member', secondary='event_participants', backref='events')
    created_by = db.relationship('User', backref='created_events')

class EventParticipant(db.Model):
    __tablename__ = 'event_participants'
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), primary_key=True)
    registration_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='registered')  # registered, cancelled, attended
    payment_status = db.Column(db.String(20), nullable=True)  # paid, pending, refunded

class JobOffer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    contract_type = db.Column(db.String(50), nullable=False)  # CDI, CDD, Stage, etc.
    salary_range = db.Column(db.String(100), nullable=True)
    posted_by_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, filled, expired
    requirements = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(120), nullable=False)
    remote_policy = db.Column(db.String(50), nullable=True)  # on-site, hybrid, remote
    
    # Relations
    posted_by = db.relationship('Member', backref='job_offers')
    applications = db.relationship('JobApplication', backref='job_offer', lazy=True)

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_offer.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    cover_letter = db.Column(db.Text, nullable=True)
    resume_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relations
    applicant = db.relationship('Member', backref='job_applications')

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # announcement, news, success-story
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='draft')  # draft, published
    
    # Relations
    author = db.relationship('User', backref='news_articles')

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenoms = db.Column(db.String(100), nullable=False)
    promo = db.Column(db.Integer, nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    ville_residence = db.Column(db.String(100), nullable=False)
    pays_residence = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Nouveaux champs
    linkedin_url = db.Column(db.String(500), nullable=True)
    current_company = db.Column(db.String(200), nullable=True)
    current_position = db.Column(db.String(200), nullable=True)
    skills = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    is_mentor = db.Column(db.Boolean, default=False)
    mentor_topics = db.Column(db.Text, nullable=True)
    profile_picture_url = db.Column(db.String(500), nullable=True)
    newsletter_subscription = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, inactive, banned

    def geocode_address(self):
        try:
            geolocator = Nominatim(user_agent='mis_association')
            location = geolocator.geocode(f"{self.ville_residence}, {self.pays_residence}")
            if location:
                self.latitude = location.latitude
                self.longitude = location.longitude
                return True
        except GeocoderTimedOut:
            pass
        return False

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), db.ForeignKey('member.email'), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relation avec Member
    member = db.relationship('Member', backref=db.backref('user', uselist=False))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                           algorithms=['HS256'])['reset_password']
        except:
            return None
        return User.query.get(id)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Demander la réinitialisation')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nouveau mot de passe', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Réinitialiser le mot de passe')

class FirstLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Choisissez un mot de passe', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Créer mon compte')

class EventForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    date = DateTimeField('Date et heure', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    location = StringField('Lieu', validators=[DataRequired()])
    event_type = SelectField('Type d’événement', choices=[
        ('afterwork', 'Afterwork'),
        ('conference', 'Conférence'),
        ('formation', 'Formation'),
        ('networking', 'Networking'),
        ('other', 'Autre')
    ])
    max_participants = IntegerField('Nombre maximum de participants', validators=[Optional(), NumberRange(min=1)])
    price = FloatField('Prix (€)', validators=[Optional(), NumberRange(min=0)])
    is_online = BooleanField('Événement en ligne')
    meeting_link = StringField('Lien de réunion', validators=[Optional(), URL()])
    image_url = StringField('URL de l’image', validators=[Optional(), URL()])
    submit = SubmitField('Enregistrer')

class JobOfferForm(FlaskForm):
    title = StringField('Titre du poste', validators=[DataRequired(), Length(min=5, max=200)])
    company = StringField('Entreprise', validators=[DataRequired(), Length(min=2, max=200)])
    description = TextAreaField('Description du poste', validators=[DataRequired()])
    location = StringField('Localisation', validators=[DataRequired()])
    contract_type = SelectField('Type de contrat', choices=[
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('stage', 'Stage'),
        ('alternance', 'Alternance'),
        ('freelance', 'Freelance')
    ])
    salary_range = StringField('Fourchette de salaire')
    requirements = TextAreaField('Prérequis')
    contact_email = StringField('Email de contact', validators=[DataRequired(), Email()])
    remote_policy = SelectField('Politique de télétravail', choices=[
        ('on-site', 'Sur site'),
        ('hybrid', 'Hybride'),
        ('remote', 'Télétravail total')
    ])
    expires_at = DateField('Date d’expiration', validators=[Optional()])
    submit = SubmitField('Publier l’offre')

class JobApplicationForm(FlaskForm):
    cover_letter = TextAreaField('Lettre de motivation', validators=[DataRequired()])
    resume_url = StringField('Lien vers votre CV', validators=[Optional(), URL()])
    submit = SubmitField('Postuler')

class NewsForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired(), Length(min=5, max=200)])
    content = TextAreaField('Contenu', validators=[DataRequired()])
    category = SelectField('Catégorie', choices=[
        ('announcement', 'Annonce'),
        ('news', 'Actualité'),
        ('success-story', 'Success Story')
    ])
    image_url = StringField('URL de l’image', validators=[Optional(), URL()])
    status = SelectField('Statut', choices=[
        ('draft', 'Brouillon'),
        ('published', 'Publié')
    ])
    submit = SubmitField('Enregistrer')

class MemberProfileForm(FlaskForm):
    linkedin_url = StringField('Profil LinkedIn', validators=[Optional(), URL()])
    current_company = StringField('Entreprise actuelle')
    current_position = StringField('Poste actuel')
    skills = TextAreaField('Compétences')
    bio = TextAreaField('Biographie')
    is_mentor = BooleanField('Je souhaite devenir mentor')
    mentor_topics = TextAreaField('Domaines de mentorat')
    profile_picture_url = StringField('URL de la photo de profil', validators=[Optional(), URL()])
    newsletter_subscription = BooleanField('Je souhaite recevoir la newsletter')
    submit = SubmitField('Mettre à jour mon profil')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')
    first_login = SubmitField('Première connexion')
    reset_password = SubmitField('Mot de passe oublié')

class RegisterForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    prenoms = StringField('Prénoms', validators=[DataRequired(), Length(min=2, max=100)])
    promo = IntegerField('Promotion', validators=[DataRequired(), NumberRange(min=1994, max=2027, message='La promotion doit être comprise entre 1994 et 2027')])
    telephone = StringField('Numéro de téléphone', validators=[DataRequired(), Length(min=8, max=20), Regexp('^[0-9]+$', message='Le numéro de téléphone doit contenir uniquement des chiffres')])
    email = StringField('Email', validators=[DataRequired(), Email()])
    ville_residence = StringField('Ville de résidence', validators=[DataRequired()],
                                render_kw={'class': 'form-control select2',
                                          'data-placeholder': 'Sélectionnez une ville'})
    pays_residence = StringField('Pays de résidence', validators=[DataRequired()],
                               render_kw={'class': 'form-control select2',
                                         'data-placeholder': 'Sélectionnez un pays'})
    submit = SubmitField('S\'inscrire')

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut


class EmailSearchForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Rechercher')

class MemberForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    prenoms = StringField('Prénoms', validators=[DataRequired(), Length(min=2, max=100)])
    promo = IntegerField('Promotion', validators=[DataRequired(), NumberRange(min=1994, max=2027, message='La promotion doit être comprise entre 1994 et 2027')])
    telephone = StringField('Numéro de téléphone', validators=[DataRequired(), Length(min=8, max=20), Regexp('^[0-9]+$', message='Le numéro de téléphone doit contenir uniquement des chiffres')])
    email = StringField('Email', validators=[DataRequired(), Email()])
    ville_residence = StringField('Ville de résidence', validators=[DataRequired()],
                                render_kw={'class': 'form-control select2',
                                          'data-placeholder': 'Sélectionnez une ville'})
    pays_residence = StringField('Pays de résidence', validators=[DataRequired()],
                               render_kw={'class': 'form-control select2',
                                         'data-placeholder': 'Sélectionnez un pays'})
    submit = SubmitField('Enregistrer')

# Exemple d'événements (plus tard, nous les stockerons en base de données)
EVENTS = [
    {
        'title': 'Afterwork MIS à Paris',
        'description': 'Rejoignez-nous pour un afterwork convivial au cœur de Paris. Une occasion unique de networker avec d\'autres diplômés MIS.',
        'date': '15 avril 2025',
        'image': 'https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=800&q=80',
        'link': '#'
    },
    {
        'title': 'Conférence IA & Big Data',
        'description': 'Une journée de conférences sur les dernières tendances en IA et Big Data, animée par des experts du domaine.',
        'date': '5 mai 2025',
        'image': 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=800&q=80',
        'link': '#'
    },
    {
        'title': 'Workshop Cloud Computing',
        'description': 'Workshop pratique sur les architectures cloud modernes. Places limitées, inscrivez-vous rapidement !',
        'date': '20 mai 2025',
        'image': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80',
        'link': '#'
    }
]

@app.route('/')
def index():
    return render_template('index.html', events=EVENTS)



@app.route('/network-map')
def network_map():
    # Récupérer les filtres
    selected_promo = request.args.get('promo')
    selected_pays = request.args.get('pays')
    selected_ville = request.args.get('ville')

    # Construire la requête de base
    query = Member.query

    # Appliquer les filtres
    if selected_promo:
        query = query.filter(Member.promo == selected_promo)
    if selected_pays:
        query = query.filter(Member.pays_residence == selected_pays)
    if selected_ville:
        query = query.filter(Member.ville_residence == selected_ville)

    # Récupérer les listes pour les filtres
    promos = db.session.query(Member.promo).distinct().order_by(Member.promo.desc()).all()
    promos = [p[0] for p in promos]
    pays = db.session.query(Member.pays_residence).distinct().order_by(Member.pays_residence).all()
    pays = [p[0] for p in pays]
    villes = db.session.query(Member.ville_residence).distinct().order_by(Member.ville_residence).all()
    villes = [v[0] for v in villes]

    # Récupérer les membres avec leurs coordonnées
    members = query.order_by(Member.nom).all()
    member_locations = [{
        'name': f"{m.prenoms} {m.nom}",
        'lat': m.latitude,
        'lng': m.longitude,
        'info': f"MIS {m.promo}, {m.ville_residence}, {m.pays_residence}",
        'email': m.email,
        'linkedin_url': m.linkedin_url
    } for m in members if m.latitude and m.longitude]

    # Calculer les statistiques
    total_members = len(member_locations)
    total_countries = len(pays)
    total_promos = len(promos)

    return render_template('network_map.html',
                         promos=promos,
                         pays=pays,
                         villes=villes,
                         selected_promo=selected_promo,
                         selected_pays=selected_pays,
                         selected_ville=selected_ville,
                         member_locations=member_locations,
                         total_members=total_members,
                         total_countries=total_countries,
                         total_promos=total_promos)

@app.route('/directory')
def directory():
    # Get filter values from request
    selected_promo = request.args.get('promo', '')
    selected_pays = request.args.get('pays', '')
    selected_ville = request.args.get('ville', '')

    # Base query
    query = Member.query

    # Apply filters
    if selected_promo:
        query = query.filter(Member.promo == int(selected_promo))
    if selected_pays:
        query = query.filter(Member.pays_residence == selected_pays)
    if selected_ville:
        query = query.filter(Member.ville_residence == selected_ville)

    # Get distinct values for filter dropdowns
    promos = db.session.query(Member.promo).distinct().order_by(Member.promo.desc()).all()
    pays = db.session.query(Member.pays_residence).distinct().order_by(Member.pays_residence).all()
    villes = db.session.query(Member.ville_residence).distinct().order_by(Member.ville_residence).all()

    # Execute filtered query
    members = query.order_by(Member.nom).all()
    members_list = [{
        'id': m.id,
        'nom': m.nom,
        'prenoms': m.prenoms,
        'promo': m.promo,
        'email': m.email,
        'ville_residence': m.ville_residence,
        'pays_residence': m.pays_residence,
        'latitude': m.latitude,
        'longitude': m.longitude
    } for m in members]

    return render_template('directory.html',
                         members=members_list,
                         promos=[p[0] for p in promos],
                         pays=[p[0] for p in pays],
                         villes=[v[0] for v in villes],
                         selected_promo=selected_promo,
                         selected_pays=selected_pays,
                         selected_ville=selected_ville)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        email = request.form.get('email')
        member = Member.query.filter_by(email=email).first()
        return render_template('search.html', member=member)
    return render_template('search.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegisterForm()
    if form.validate_on_submit():
        # Vérifier si l'email existe déjà
        if Member.query.filter_by(email=form.email.data).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('register.html', form=form, pays_list=COUNTRIES)

        # Créer le membre
        member = Member(
            email=form.email.data,
            nom=form.nom.data,
            prenoms=form.prenoms.data,
            promo=form.promo.data,
            telephone=form.telephone.data,
            ville_residence=form.ville_residence.data,
            pays_residence=form.pays_residence.data
        )

        # Géocoder l'adresse
        member.geocode_address()

        try:
            print(f"Tentative d'ajout du membre: {member.email}")
            db.session.add(member)
            print("Tentative de commit")
            db.session.commit()
            print("Inscription réussie")
            flash('Inscription réussie ! Vous pouvez maintenant créer votre compte utilisateur.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Erreur lors de l'inscription: {str(e)}")
            db.session.rollback()
            flash('Une erreur est survenue lors de l\'inscription. Veuillez réessayer.', 'danger')
            return render_template('register.html', form=form, pays_list=COUNTRIES)

    return render_template('register.html', form=form, pays_list=COUNTRIES)

@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        member = Member.query.filter_by(email=form.email.data).first()
        if member:
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                if send_password_reset_email(user):
                    flash('Un email avec les instructions de réinitialisation a été envoyé.', 'info')
                    return redirect(url_for('login'))
                else:
                    flash('Une erreur est survenue lors de l\'envoi de l\'email. Veuillez réessayer.', 'danger')
            else:
                flash('Veuillez d\'abord créer votre compte utilisateur.', 'warning')
                return redirect(url_for('first_login'))
        else:
            flash('Aucun membre trouvé avec cette adresse email.', 'danger')
    return render_template('reset_password_request.html', title='Réinitialisation du mot de passe', form=form)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # TODO: Vérifier le token
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Votre mot de passe a été réinitialisé.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

@app.route('/first-login', methods=['GET', 'POST'])
def first_login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = FirstLoginForm()
    if form.validate_on_submit():
        # Vérifier si le membre existe
        member = Member.query.filter_by(email=form.email.data).first()
        if not member:
            flash('Aucun membre trouvé avec cet email. Veuillez vous inscrire d\'abord.', 'danger')
            return redirect(url_for('register'))
        
        # Vérifier si un compte utilisateur existe déjà
        if User.query.filter_by(email=form.email.data).first():
            flash('Un compte utilisateur existe déjà pour cet email.', 'danger')
            return redirect(url_for('login'))
        
        # Créer le compte utilisateur
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Compte utilisateur créé avec succès !', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue. Veuillez réessayer.', 'danger')
    
    return render_template('first_login.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    # Si le bouton "Première connexion" est cliqué
    if form.first_login.data:
        return redirect(url_for('first_login'))
    
    # Si le bouton "Mot de passe oublié" est cliqué
    if form.reset_password.data:
        return redirect(url_for('reset_password_request'))
    
    if form.validate_on_submit() and form.submit.data:
        member = Member.query.filter_by(email=form.email.data).first()
        if not member:
            flash('Email inconnu.', 'danger')
            return render_template('login.html', form=form)
        
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash('Veuillez créer votre compte utilisateur.', 'info')
            return redirect(url_for('first_login'))
        
        if user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        
        flash('Mot de passe incorrect.', 'danger')
    
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
    # Récupérer les paramètres de filtre
    promotion = request.args.get('promotion')
    ville = request.args.get('ville')
    pays = request.args.get('pays')

    # Construire la requête de base
    query = Member.query

    # Appliquer les filtres
    if promotion:
        query = query.filter(Member.promo == int(promotion))
    if ville:
        query = query.filter(Member.ville_residence.ilike(f'%{ville}%'))
    if pays:
        query = query.filter(Member.pays_residence.ilike(f'%{pays}%'))

    # Récupérer les valeurs distinctes pour les filtres
    promotions = db.session.query(Member.promo).distinct().order_by(Member.promo).all()
    villes = db.session.query(Member.ville_residence).distinct().order_by(Member.ville_residence).all()
    pays_list = db.session.query(Member.pays_residence).distinct().order_by(Member.pays_residence).all()

    # Exécuter la requête finale
    members = query.order_by(Member.nom).all()

    return render_template('admin.html', 
                         members=members,
                         promotions=[p[0] for p in promotions],
                         villes=[v[0] for v in villes],
                         pays_list=[p[0] for p in pays_list],
                         selected_promotion=promotion,
                         selected_ville=ville,
                         selected_pays=pays)

@app.route('/export-csv')
@login_required
def export_csv():
    # Get filter values from request
    promo_filter = request.args.get('promo', '')
    pays_filter = request.args.get('pays', '')
    ville_filter = request.args.get('ville', '')

    # Base query
    query = Member.query

    # Apply filters
    if promo_filter:
        query = query.filter(Member.promo == int(promo_filter))
    if pays_filter:
        query = query.filter(Member.pays_residence.ilike(f'%{pays_filter}%'))
    if ville_filter:
        query = query.filter(Member.ville_residence.ilike(f'%{ville_filter}%'))

    # Get filtered members
    members = query.order_by(Member.nom).all()
    
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
    
    # Générer le nom du fichier en fonction des filtres
    filename = 'membres_mis'
    if promo_filter:
        filename += f'_promo{promo_filter}'
    if pays_filter:
        filename += f'_{pays_filter}'
    if ville_filter:
        filename += f'_{ville_filter}'
    filename += '.csv'
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
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

        # Géocodage de la nouvelle adresse
        if member.geocode_address():
            try:
                db.session.commit()
                flash('Informations mises à jour avec succès!', 'success')
                return redirect(url_for('search'))
            except:
                db.session.rollback()
                flash('Une erreur est survenue lors de la mise à jour.', 'error')
        else:
            flash('Impossible de géocoder la nouvelle adresse. Veuillez vérifier la ville et le pays.', 'warning')
    return render_template('edit.html', form=form, member=member)

@app.cli.command('create-admin')
def create_admin():
    """Créer un nouvel administrateur"""
    email = input('Email: ')
    password = input('Mot de passe: ')
    nom = input('Nom: ')
    prenoms = input('Prénoms: ')
    
    # Créer d'abord le membre admin
    admin_member = Member(
        email=email,
        nom=nom,
        prenoms=prenoms,
        promo=2000,  # Valeur par défaut
        telephone='0000000000',  # Valeur par défaut
        ville_residence='Paris',  # Valeur par défaut
        pays_residence='France'  # Valeur par défaut
    )
    admin_member.geocode_address()
    
    # Créer l'utilisateur admin
    admin_user = User(email=email, is_admin=True)
    admin_user.set_password(password)
    
    with app.app_context():
        try:
            db.session.add(admin_member)
            db.session.add(admin_user)
            db.session.commit()
            print(f'Administrateur {email} créé avec succès!')
        except Exception as e:
            db.session.rollback()
            print(f'Erreur lors de la création de l\'administrateur: {str(e)}')

@app.cli.command('reset-admin')
def reset_admin():
    """Réinitialiser l'administrateur avec les identifiants par défaut"""
    with app.app_context():
        # Supprimer tous les administrateurs existants
        User.query.filter_by(is_admin=True).delete()
        
        # Créer le membre admin par défaut
        admin_member = Member(
            email='admin@example.com',
            nom='Admin',
            prenoms='System',
            promo=2000,
            telephone='0000000000',
            ville_residence='Paris',
            pays_residence='France'
        )
        admin_member.geocode_address()
        
        # Créer l'utilisateur admin par défaut
        admin_user = User(email='admin@example.com', is_admin=True)
        admin_user.set_password('admin')
        
        try:
            db.session.add(admin_member)
            db.session.add(admin_user)
            db.session.commit()
            print('Administrateur réinitialisé avec succès!')
        except Exception as e:
            db.session.rollback()
            print(f'Erreur lors de la réinitialisation de l\'administrateur: {str(e)}')
        admin = Admin(username='admin')
        admin.set_password('admin')
        
        db.session.add(admin)
        db.session.commit()
        print('Administrateur réinitialisé avec succès!')
        print('Nom d\'utilisateur: admin')
        print('Mot de passe: admin')

# Routes pour l'autocomplétion
@app.route('/api/countries')
def get_countries():
    return jsonify([{'name': country} for country in COUNTRIES])

@app.route('/api/cities')
def get_cities():
    country = request.args.get('country', '')
    search = request.args.get('q', '')
    
    if not search or not country:
        return jsonify([])
    
    # Utiliser l'API GeoNames pour obtenir les villes
    url = 'http://api.geonames.org/searchJSON'
    params = {
        'name_startsWith': search,
        'country': country,
        'featureClass': 'P',
        'maxRows': 10,
        'username': 'hardysawadogo',
        'style': 'SHORT'
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        cities = [{'name': city['name']} for city in data.get('geonames', [])]
        return jsonify(cities)
    except Exception as e:
        print(f'Error fetching cities: {str(e)}')
        return jsonify([])

def send_password_reset_email(user):
    try:
        token = user.get_reset_password_token()
        msg = Message('Réinitialisation de votre mot de passe',
                      recipients=[user.email])
        msg.body = f'''
        Pour réinitialiser votre mot de passe, cliquez sur le lien suivant :
        {url_for('reset_password', token=token, _external=True)}
        
        Si vous n'avez pas demandé de réinitialisation de mot de passe, ignorez ce message.
        '''
        mail.send(msg)
        return True
    except Exception as e:
        print(f'Erreur lors de l\'envoi de l\'email : {str(e)}')
        return False

def init_db():
    with app.app_context():
        # Supprimer toutes les tables existantes
        db.drop_all()
        # Créer les tables
        db.create_all()
        print("Tables recréées avec succès")

@app.route('/recensement', methods=['GET', 'POST'])
def recensement():
    form = MemberForm()
    if form.validate_on_submit():
        member = Member.query.filter_by(email=form.email.data).first()
        if member:
            flash('Un membre avec cet email existe déjà.', 'danger')
            return redirect(url_for('recensement'))

        member = Member(
            nom=form.nom.data,
            prenoms=form.prenoms.data,
            promo=form.promo.data,
            telephone=form.telephone.data,
            email=form.email.data,
            ville_residence=form.ville_residence.data,
            pays_residence=form.pays_residence.data
        )
        member.geocode_address()
        db.session.add(member)
        db.session.commit()
        return render_template('recensement_success.html', member=member)
    return render_template('recensement.html', form=form, countries=COUNTRIES)

@app.route('/verifier-membre', methods=['GET', 'POST'])
def verifier_membre():
    form = EmailSearchForm()
    member = None
    if form.validate_on_submit():
        member = Member.query.filter_by(email=form.email.data).first()
        if not member:
            flash('Aucun membre trouvé avec cet email.', 'danger')
    return render_template('verifier_membre.html', form=form, member=member)

# Dictionnaire des coordonnées des villes
CITY_COORDINATES = {
    ('Abidjan', 'CÔTE D\'IVOIRE'): (5.3596, -4.0083),
    ('Abdjan', 'CÔTE D\'IVOIRE'): (5.3596, -4.0083),  # correction d'orthographe
    ('Abidjan Cocody', 'CÔTE D\'IVOIRE'): (5.3596, -4.0083),
    ('Abobo', 'CÔTE D\'IVOIRE'): (5.4364, -4.0163),
    ('Bingerville', 'CÔTE D\'IVOIRE'): (5.3500, -3.8833),
    ('Bouake', 'CÔTE D\'IVOIRE'): (7.6833, -5.0333),
    ('Yamoussoukro', 'CÔTE D\'IVOIRE'): (6.8276, -5.2892),
    ('Yamoussoukro/Man', 'CÔTE D\'IVOIRE'): (6.8276, -5.2892),
    ('Grand Bassam', 'CÔTE D\'IVOIRE'): (5.2118, -3.7419),
    ('Paris', 'FRANCE'): (48.8566, 2.3522),
    ('Lyon', 'FRANCE'): (45.7578, 4.8320),
    ('Rennes', 'FRANCE'): (48.1173, -1.6778),
    ('Nantes', 'FRANCE'): (47.2184, -1.5536),
    ('Lille', 'FRANCE'): (50.6292, 3.0573),
    ('Grenoble', 'FRANCE'): (45.1885, 5.7245),
    ('Région Parisienne', 'FRANCE'): (48.8566, 2.3522),
    ('Bruxelles', 'BELGIQUE'): (50.8503, 4.3517),
    ('Ouagadougou', 'BURKINA FASO'): (12.3714, -1.5197),
    ('Ziniaré', 'BURKINA FASO'): (12.5822, -1.2967),
    ('Douala', 'CAMEROUN'): (4.0511, 9.7679),
    ('Yaoundé', 'CAMEROUN'): (3.8480, 11.5021),
    ('Montreal', 'CANADA'): (45.5017, -73.5673),
    ('Ottawa', 'CANADA'): (45.4215, -75.6972),
    ('Quebec', 'CANADA'): (46.8139, -71.2080),
    ('Québec', 'CANADA'): (46.8139, -71.2080),
    ('Trois-Rivières', 'CANADA'): (46.3432, -72.5429),
    ('Accra', 'GHANA'): (5.6037, -0.1870),
    ('Differdange', 'LUXEMBOURG'): (49.5244, 5.8889),
    ('Casablanca', 'MAROC'): (33.5731, -7.5898),
    ('Tomar', 'PORTUGAL'): (39.6044, -8.4075),
    ('Dakar', 'SÉNÉGAL'): (14.7167, -17.4677),
    ('Lomé', 'TOGO'): (6.1285, 1.2255),
    ('Istanbul', 'TURKEY'): (41.0082, 28.9784),
}

def standardize_city(city, country):
    # Standardisation des noms de villes et pays
    city = city.strip()
    country = country.strip()
    
    # Corrections spécifiques
    if city == 'Abdjan':
        city = 'Abidjan'
    elif 'Abidjan' in city:
        city = 'Abidjan'
    elif 'Paris' in city or 'Région Parisienne' in city:
        city = 'Paris'
    
    return city, country

def import_members_from_csv(csv_file_path):
    with app.app_context():
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # Skip empty rows or header
                if not row['email'] or row['Pays'] == 'Pays':
                    continue
                
                # Standardiser la ville et le pays
                city, country = standardize_city(row['Ville'], row['Pays'])
                
                member = Member(
                    promo=int(row['Promotion']),
                    prenoms=row['Prenoms'],
                    nom=row['Nom'],
                    pays_residence=country,
                    ville_residence=city,
                    telephone=row['contact'],
                    email=row['email']
                )
                
                # Utiliser les coordonnées prédéfinies
                coords = CITY_COORDINATES.get((city, country))
                if coords:
                    member.latitude, member.longitude = coords
                    print(f"Coordonnées trouvées pour {city}, {country}: {coords}")
                else:
                    print(f"Pas de coordonnées pour {city}, {country}")
                
                # Check if member already exists
                existing_member = Member.query.filter_by(email=row['email']).first()
                if existing_member is None:
                    db.session.add(member)
            
            try:
                db.session.commit()
                print("Members imported successfully")
            except Exception as e:
                db.session.rollback()
                print(f"Error importing members: {str(e)}")

if __name__ == '__main__':
    init_db()
    import_members_from_csv('/Users/hardysmile/Downloads/Liste MIS 08_2024 - template.csv')
    app.run(debug=True, port=5030)
