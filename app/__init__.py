import logging

from flask import Flask
from flask_appbuilder import AppBuilder, SQLA
from flask_mail import Mail
from flask_migrate import Migrate

from app.index import Index

"""
 Logging configuration
"""

logging.basicConfig(format="%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object("config")
db = SQLA(app)
mail = Mail(app)
migrate = Migrate(app, db)
appbuilder = AppBuilder(app, db.session, indexview=Index, base_template="base.html")


"""
from sqlalchemy.engine import Engine
from sqlalchemy import event

#Only include this for SQLLite constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Will force sqllite contraint foreign keys
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
"""

from . import views
