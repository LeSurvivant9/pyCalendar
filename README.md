# pyCalendar

Ce programme permet de synchroniser les événements de l'ENT avec Google Calendar. Suivez les instructions ci-dessous
pour configurer et exécuter le programme sur votre machine.

## Prérequis

- Git
- Python 3.x
- pip (généralement installé avec Python)
- Chrome (pour selenium)

## Installation

1. **Cloner le dépôt GitHub**

   Ouvrez un terminal et exécutez la commande suivante pour cloner le dépôt :

  ```bash
   git clone https://github.com/LeSurvivant9/pyCalendar.git
  ```

2. **Créer un environnement virtuel**

  ```bash
  cd pyCalendar
  python -m venv venv
  ```

Ceci crée un environnement virtuel nommé `venv` dans le dossier courant.

3. **Activer l'environnement virtuel**

- Sous Windows, exécutez :

  ```bash
  .\venv\Scripts\activate
  ```

- Sous MacOS/Linux, exécutez :

  ```bash
  source venv/bin/activate
  ```

4. **Mise à jour de pip**

Assurez-vous que pip est à jour :

  ```bash
  pip install --upgrade pip
  ```

5. **Installation des dépendances**

Installez toutes les dépendances nécessaires en exécutant :

  ```bash
 pip install -r requirements.txt
  ```

6. **Configurer les identifiants ENT**

Créez un fichier `.env` à la racine du projet et ajoutez vos identifiants ENT :

  ```
    ENT_USERNAME=VotreIdentifiant
    ENT_PASSWORD=VotreMotDePasse
  ```

Remplacez `monIdentifiant` et `monMotDePasse` par vos véritables identifiants ENT.

7. **Lancer le programme**

Vous pouvez maintenant lancer le programme via le terminal/cmd ou via votre IDE préféré en exécutant :

  ```bash
    python main.py
  ```

8. **Autorisation d'accès à Google Calendar**

Lors du premier lancement, un navigateur s'ouvrira vous demandant d'autoriser `pyCalendar` à accéder à votre Google
Calendar. Suivez les instructions à l'écran pour accorder l'accès.

9. **Laissez faire la magie**

Une fois toutes les étapes précédentes complétées, le programme synchronisera automatiquement les événements de l'ENT
avec votre Google Calendar.
