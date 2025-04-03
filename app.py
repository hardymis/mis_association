from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify
import requests

import pycountry

# Liste des pays en français avec leurs noms en anglais
COUNTRIES = sorted([country.name for country in pycountry.countries])
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
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = MemberForm()
    if form.validate_on_submit():
        # Vérifier si l'email existe déjà
        existing_member = Member.query.filter_by(email=form.email.data).first()
        if existing_member:
            flash('Un membre avec cet email existe déjà. Veuillez utiliser un autre email ou modifier les informations existantes via la recherche.', 'error')
            return render_template('register.html', form=form, pays_list=COUNTRIES)

        member = Member(
            nom=form.nom.data,
            prenoms=form.prenoms.data,
            promo=form.promo.data,
            telephone=form.telephone.data,
            email=form.email.data,
            ville_residence=form.ville_residence.data,
            pays_residence=form.pays_residence.data
        )

        # Géocodage de l'adresse
        if member.geocode_address():
            try:
                db.session.add(member)
                db.session.commit()
                flash('Inscription réussie!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash('Une erreur est survenue lors de l\'enregistrement. Veuillez réessayer.', 'error')
        else:
            flash('Impossible de géocoder l\'adresse. Veuillez vérifier la ville et le pays.', 'warning')
    return render_template('register.html', form=form, pays_list=COUNTRIES)

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
        query = query.filter(Member.promotion == selected_promo)
    if selected_pays:
        query = query.filter(Member.pays == selected_pays)
    if selected_ville:
        query = query.filter(Member.ville == selected_ville)

    # Récupérer les listes pour les filtres
    promos = db.session.query(Member.promotion).distinct().order_by(Member.promotion.desc()).all()
    promos = [p[0] for p in promos]
    pays = db.session.query(Member.pays).distinct().order_by(Member.pays).all()
    pays = [p[0] for p in pays]
    villes = db.session.query(Member.ville).distinct().order_by(Member.ville).all()
    villes = [v[0] for v in villes]

    # Récupérer les membres avec leurs coordonnées
    members = query.order_by(Member.nom).all()
    member_locations = [{
        'name': f"{m.prenom} {m.nom}",
        'lat': m.latitude,
        'lng': m.longitude,
        'info': f"Promotion {m.promotion}<br>Ville: {m.ville}, {m.pays}"
    } for m in members if m.latitude and m.longitude]

    return render_template('network_map.html',
                         promos=promos,
                         pays=pays,
                         villes=villes,
                         selected_promo=selected_promo,
                         selected_pays=selected_pays,
                         selected_ville=selected_ville,
                         member_locations=member_locations)

@app.route('/directory')
def directory():
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
                         selected_promo=promo_filter,
                         selected_pays=pays_filter,
                         selected_ville=ville_filter)

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
    username = input('Nom d\'utilisateur: ')
    password = input('Mot de passe: ')
    
    admin = Admin(username=username)
    admin.set_password(password)
    
    with app.app_context():
        db.session.add(admin)
        db.session.commit()
        print(f'Administrateur {username} créé avec succès!')

@app.cli.command('reset-admin')
def reset_admin():
    """Réinitialiser l'administrateur avec les identifiants par défaut"""
    with app.app_context():
        # Supprimer tous les administrateurs existants
        Admin.query.delete()
        
        # Créer le nouvel administrateur
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5010)
