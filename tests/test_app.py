import pytest
from flask import get_flashed_messages
from app import app, db, Member, Admin
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Créer un admin de test
            admin = Admin(username='testadmin')
            admin.set_password('testpass123')
            db.session.add(admin)
            
            # Créer quelques membres de test
            members = [
                Member(
                    nom='Doe',
                    prenoms='John',
                    promo=2020,
                    telephone='1234567890',
                    email='john.doe@test.com',
                    ville_residence='Paris',
                    pays_residence='France'
                ),
                Member(
                    nom='Smith',
                    prenoms='Jane',
                    promo=2021,
                    telephone='0987654321',
                    email='jane.smith@test.com',
                    ville_residence='Lyon',
                    pays_residence='France'
                )
            ]
            db.session.add_all(members)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def test_index_page(client):
    """Test de la page d'accueil"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'MIS Association' in response.data

def test_register_page(client):
    """Test de la page d'inscription"""
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Inscription' in response.data

def test_successful_registration(client):
    """Test d'une inscription réussie"""
    data = {
        'nom': 'Test',
        'prenoms': 'User',
        'promo': 2022,
        'telephone': '1122334455',
        'email': 'test.user@test.com',
        'ville_residence': 'Paris',
        'pays_residence': 'France'
    }
    response = client.post('/register', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Inscription r\xc3\xa9ussie' in response.data

def test_duplicate_email_registration(client):
    """Test d'une inscription avec un email déjà utilisé"""
    data = {
        'nom': 'Duplicate',
        'prenoms': 'User',
        'promo': 2022,
        'telephone': '1122334455',
        'email': 'john.doe@test.com',  # Email déjà utilisé
        'ville_residence': 'Paris',
        'pays_residence': 'France'
    }
    response = client.post('/register', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'existe d\xc3\xa9j\xc3\xa0' in response.data

def test_admin_login_success(client):
    """Test de connexion admin réussie"""
    data = {
        'username': 'testadmin',
        'password': 'testpass123'
    }
    response = client.post('/login', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Administration' in response.data

def test_admin_login_failure(client):
    """Test de connexion admin échouée"""
    data = {
        'username': 'testadmin',
        'password': 'wrongpass'
    }
    response = client.post('/login', data=data, follow_redirects=True)
    assert response.status_code == 200
    # Vérifie que le message d'erreur est dans la réponse HTML
    assert b'danger' in response.data and b'Nom d&#39;utilisateur ou mot de passe incorrect' in response.data

def test_admin_required_pages(client):
    """Test des pages nécessitant une connexion admin"""
    pages = ['/admin', '/export-csv']
    for page in pages:
        response = client.get(page)
        assert response.status_code == 302  # Redirection vers login

def test_member_filters(client):
    """Test des filtres de membres"""
    # Login admin
    client.post('/login', data={'username': 'testadmin', 'password': 'testpass123'})
    
    # Test filtre par promotion
    response = client.get('/admin?promotion=2020')
    assert response.status_code == 200
    assert b'John' in response.data
    assert b'Jane' not in response.data
    
    # Test filtre par ville
    response = client.get('/admin?ville=Lyon')
    assert response.status_code == 200
    assert b'Jane' in response.data
    assert b'John' not in response.data

def test_api_endpoints(client):
    """Test des endpoints API"""
    # Test de l'API des pays
    response = client.get('/api/countries')
    assert response.status_code == 200
    assert b'France' in response.data
    
    # Test de l'API des villes avec GeoNames mock
    with app.test_client() as client:
        with app.app_context():
            # On ne teste que le statut car les résultats dépendent de l'API externe
            response = client.get('/api/cities?country=France&q=Par')
            assert response.status_code == 200
