from app import app, db
from flask_migrate import Migrate, init, migrate, upgrade
import os

migrate_ext = Migrate(app, db, directory="db_migrations")

with app.app_context():
    if not os.path.exists("db_migrations"):
        print("Initializing migrations directory...")
        init(directory="db_migrations")
    print("Generating migrations...")
    migrate(directory="db_migrations", message="auto migration")
    print("Applying migrations...")
    upgrade(directory="db_migrations")
