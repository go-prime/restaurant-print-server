

from flask import Flask, jsonify, request, session, g
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
# from loggers import logger
from flask_dotenv import DotEnv
from physical_print import PrintError, print_job, get_session
from loggers import logger
from dotenv import load_dotenv
import os
import traceback

app = Flask(__name__)
login_manager = LoginManager()

SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///print.db"

db = SQLAlchemy(app)
env = DotEnv(app)
login_manager.init_app(app)
app.secret_key = os.environ.get("SECRET_KEY")


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Clean up database session at end of request."""
    session = g.pop('db_session', None)
    if session is not None:
        if exception:
            session.rollback()
        else:
            session.commit()
        session.close()


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route("/v1/login", methods=["POST"])
def login():
    '''Creates a user session'''
    if request.method == 'POST':
        posted_data = request.get_json()

        if (dict(request.headers).get("Authorization") == app.config.get('API_KEY') and
                posted_data.get('password') == app.config.get('SESSION_PASSWORD')):
            session['user'] = 1
            logger.info("Session created")
            return jsonify({
                'success': True
            })

        logger.info("Failed to create session")
        session['user'] = None
        return jsonify({
            'success': False
        })


@app.route("/v1/prints", methods=["POST"])
def prints():
    '''
    Prints documents
    receives html converts to pdf and deposits into fiscal folders
    monitors for output to make sure that the document fiscalises
    if the document is not an invoice, route the job
    directly to a print via pywin32
    logs each document created
    '''
    if not session.get('user'):
        logger.error("Attempted print job without a valid session")
        return jsonify({
            'error': "No user session detected"
        })

    if request.method != 'POST':
        logger.error("Only POST requests are allowed")
        return jsonify({
            'error': "Invalid HTTP Method, only POST permitted"
        })
    posted_data = request.get_json()
    try:
        print_job(posted_data, posted_data.get('printerCode'))
    except PrintError as e:
        logger.error("An error occurred", exc_info=True)
        return jsonify({
            'narrative': str(e),
            'success': False
        })
    except Exception as e:
        logger.error("An error occurred", exc_info=True)
        return jsonify({
            'narrative': str(e),
            'success': False
        })
    return jsonify({
        'success': True
    })


#  main thread of execution to start the server
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=9090)
