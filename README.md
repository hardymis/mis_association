# MIS Association - Application de Gestion des Membres (V1)

Application web pour la gestion des membres de l'association MIS.

## Fonctionnalités

1. **Gestion des membres**
   - Inscription avec validation des champs
   - Promotion limitée entre 1994 et 2027
   - Numéro de téléphone uniquement numérique
   - Email unique avec validation
   - Champs obligatoires : Nom, Prénoms, Promotion, Téléphone, Email, Ville et Pays de résidence

2. **Recherche de membres**
   - Recherche par email
   - Affichage détaillé des informations
   - Option de modification des informations

3. **Administration**
   - Liste complète des membres
   - Export des données en CSV
   - Compteur du nombre total de membres

## Installation

1. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix
# ou
venv\Scripts\activate  # Sur Windows
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Lancer l'application :
```bash
python app.py
```

L'application sera accessible à l'adresse : http://127.0.0.1:5008

## Technologies utilisées

- Flask
- SQLite
- Flask-SQLAlchemy
- Flask-WTF
- Bootstrap 5
- Bootstrap Icons

## Structure de la base de données

Table `Member` :
- id (Integer, Primary Key)
- nom (String)
- prenoms (String)
- promo (Integer)
- telephone (String)
- email (String, Unique)
- ville_residence (String)
- pays_residence (String)

## Routes

- `/` : Accueil
- `/register` : Inscription d'un nouveau membre
- `/search` : Recherche d'un membre par email
- `/admin` : Administration et liste des membres
- `/export-csv` : Export des données en CSV
- `/edit/<id>` : Modification des informations d'un membre
