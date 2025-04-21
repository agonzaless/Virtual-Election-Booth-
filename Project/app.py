import logging
import os
import secrets
import uuid
from collections import defaultdict
from datetime import timedelta
from datetime import timezone
from functools import wraps

import plotly
import plotly.graph_objs as go
from bson import ObjectId
from bson import json_util
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, get_flashed_messages
from flask import current_app as app
from flask import send_from_directory
from flask.json import JSONEncoder
from flask_pymongo import PyMongo
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BuildError
from datetime import datetime, UTC
from dateutil import parser



from email_handler import MultiEmailHandler
from env import *

# Load environment variables first
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)


# Create the MongoDB JSON Encoder
class MongoJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return json_util.default(obj)


# Initialize Flask app
app = Flask(__name__,
            template_folder='template',
            static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# Set up JSON encoding for the app
app.json_encoder = MongoJSONEncoder


# Add template filter for JSON conversion
@app.template_filter('tojson')
def tojson_filter(obj):
    return json_util.dumps(obj)


@app.template_filter('datetime')
def format_datetime(value, fmt=None):
    if value is None:
        return ''
    try:
        if isinstance(value, str):
            # Handle already formatted dates
            if 'AM' in value or 'PM' in value:
                return value
            # Handle ISO format dates
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value.strftime(fmt or '%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        return ''

email_handler = MultiEmailHandler(app)
print("Loaded email accounts:", [config['username'] for config in email_handler.email_configs.values()])
app.secret_key = os.getenv('ENCRYPTION_KEY')
app.config["MONGO_URI"] = "mongodb://localhost:27017/election_db"
mongo = PyMongo(app)
db = mongo.db
app.json_encoder = MongoJSONEncoder
client = MongoClient('mongodb://localhost:27017')
db = client['election_db']  # Make sure database name matches

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/candidates')

# Create the uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Email configuration
email_config = {
    'outlook': {
        'email': OUTLOOK_USERNAME_1,
        'password': OUTLOOK_PASSWORD_1,
        'smtp_server': 'smtp-mail.outlook.com',
        'smtp_port': 587
    }
}

# Set primary email provider
PRIMARY_EMAIL_PROVIDER = 'outlook'
OUTLOOK_EMAIL = 'Virtiualelection123456789@outlook.com'

# Configure Flask-Mail global settings
app.config['MAIL_SERVER'] = 'smtp.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

# Security configurations
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
UPLOAD_FOLDER = 'static/uploads/candidates'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# At the top with your imports
UPLOAD_FOLDER = 'static/uploads/candidates'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

socketio = SocketIO(app)


def save_candidate_photo(photo):
    if photo:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(photo.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        photo_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        photo.save(photo_path)
        return f'/static/uploads/candidates/{unique_filename}'


@socketio.on('new_vote')
def handle_vote(data):
    # Update stats in real-time
    updated_stats = calculate_new_stats()
    emit('stats_update', updated_stats, broadcast=True)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_voter_token():
    token = secrets.token_hex(8)  # This will generate tokens like '848beebfa2c7d245'
    expiration_time = datetime.utcnow() + timedelta(hours=24)
    return {
        'token': token,
        'expiration': expiration_time
    }


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_username' not in session:
            flash('Please log in as admin first.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated_function


# Update all candidate photo paths
db.candidates.update_many(
    {},
    {
        '$set': {
            'photo_url': {
                '$concat': [
                    '/uploads/candidates/candidates/',
                    '$photo'
                ]
            }
        }
    }
)


@app.template_filter('format_date')
def format_date(value, format='%d-%m-%YT%H:%M'):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%d-%m-%YT%H:%M')
        except ValueError:
            return value
    return value.strftime(format) if isinstance(value, datetime) else value


# Add this new route to serve uploaded files
@app.route('/uploads/candidates/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads/candidates', filename)


@app.before_request
def clear_messages():
    session.pop('_flashes', None)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    # Define the admin credentials here
    admin_username = 'admin'  # Replace with your actual admin username
    admin_password = 'password123'  # Replace with your actual admin password

    if request.method == 'POST':
        # Get the form data
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the username and password are correct
        if username == admin_username and password == admin_password:
            # Redirect to the index or admin dashboard
            return redirect(url_for('admin_dashboard'))
        else:
            # Flash an error message and stay on the login page if credentials are incorrect
            flash('Invalid username or password, please try again.', 'error')

    return render_template('admin_login.html')  # Your admin login page template


@app.route('/logout', methods=['POST'])
def logout():
    # Remove user information from session
    session.pop('admin_username', None)  # If you're storing the admin username in the session
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))  # Redirect to the index page after logging out


@app.route('/admin_dashboard')
def admin_dashboard():
    print("Admin Dashboard route accessed.")  # Add debug print to see if the route is hit
    try:
        return render_template('admin_dashboard.html')
    except Exception as e:
        print(f"Error rendering template: {e}")  # Print error message for debugging
        return f"Error: {e}"


@app.route('/admin/reset_voters', methods=['POST'])
def reset_voters():
    if session.get('is_admin'):
        # Reset all voters' status
        db.voters.update_many(
            {},
            {'$set': {'has_voted': False}}
        )
        # Clear voting records
        db.votes.delete_many({})
        # Reset voting stats
        db.voting_stats.delete_many({})

        flash('All voter records have been reset successfully!', 'success')
        return redirect(url_for('admin_dashboard'))


@app.route('/delete_election/<election_id>', methods=['POST', 'GET'])
def delete_election(election_id):
    db.elections.delete_one({'_id': ObjectId(election_id)})
    flash('Election deleted successfully!', 'success')
    return redirect(url_for('election'))


@app.route('/election', methods=['GET', 'POST'])
def election():
    try:
        if request.method == 'POST':
            election_data = create_election_data(request.form)
            result = db.elections.insert_one(election_data)

            if result.inserted_id:
                flash('Election position added successfully!', 'success')
            else:
                flash('Failed to add election position.', 'error')

            return redirect(url_for('election'))

        # Get all active elections from the MongoDB collection
        elections = list(db.elections.find({"status": "active"}).sort('created_at', -1))
        print(f"Found {len(elections)} active elections")

        if not elections:
            flash('No active elections found.', 'info')
            return render_template('election.html', elections=[], categorized_elections={})

        categorized_elections = categorize_elections(elections)
        return render_template('election.html', elections=elections, categorized_elections=categorized_elections)

    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('election'))


@app.route('/select_election/<election_id>', methods=['POST'])
def select_election(election_id):
    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if election:
            session['election_data'] = {
                'id': str(election['_id']),
                'position': election['position'],
                'category': election['category']
            }
            flash('Election selected successfully!', 'success')
            app.logger.info(f"Election selected: {election_id}")
        else:
            flash('Election not found.', 'error')
            app.logger.warning(f"Election not found: {election_id}")
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        app.logger.error(f"Error selecting election: {str(e)}", exc_info=True)
    return redirect(url_for('candidate'))

def create_election_data(form_data):
    def parse_datetime(dt_str):
        if dt_str:
            dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
            return dt.replace(tzinfo=timezone.utc)
        return None

    # Position-based category mapping
    category_mapping = {
        'executive': ['president', 'governor'],
        'legislative': ['senator', 'representative']
    }

    position = form_data.get('position', '').lower()
    category = next(
        (cat for cat, positions in category_mapping.items()
         if any(pos in position for pos in positions)),
        'other'
    )

    election_data = {
        'position': form_data.get('position'),
        'early_voting_start': parse_datetime(form_data.get('early_voting_start')),
        'early_voting_end': parse_datetime(form_data.get('early_voting_end')),
        'election_date_start': parse_datetime(form_data.get('election_date_start')),
        'election_date_end': parse_datetime(form_data.get('election_date_end')),
        'created_at': datetime.now(timezone.utc),
        'status': 'active',
        'category': category
    }

    # Convert datetime objects to ISO format strings
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in election_data.items()
    }


def categorize_elections(elections):
    return {
        'executive': [e for e in elections if e.get('category') == 'executive'],
        'legislative': [e for e in elections if e.get('category') == 'legislative'],
        'other': [e for e in elections if e.get('category') == 'other']
    }


def parse_datetime(date_string):
    if not date_string:
        return None

    try:
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash(f'Invalid date format: {date_string}. Please use YYYY-MM-DDTHH:MM format.', 'error')
        return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Generate token and expiration time
            voting_token = secrets.token_hex(8)
            expiration_time = datetime.utcnow() + timedelta(hours=24)

            dob = f"{request.form['dob-year']}-{request.form['dob-month']}-{request.form['dob-day']}"
            ssn = request.form['SSN'].replace('-', '').strip()
            email = request.form['email'].lower().strip()

            voter = {
                'first_name': request.form['first_name'].strip(),
                'last_name': request.form['last_name'].strip(),
                'email': email,
                'gender': request.form['gender'],
                'SSN': ssn,
                'DOB': dob,
                'state': request.form['state'],
                'ethnicity': request.form['ethnicity'],
                'voting_token': voting_token,
                'registration_date': datetime.utcnow(),
                'token_expiration': expiration_time,
                'status': 'active',
                'has_voted': False,
                'token_used': False
            }

            # Save to MongoDB
            result = db.voters.insert_one(voter)

            # THEN send email using the voter data
            print(f"Sending email to: {email}")
            email_html = f"""
            <html>
            <body>
                <h2>Voting Registration Confirmation</h2>
                <p>Hello {voter['first_name']} {voter['last_name']},</p>
                <p>Your voting token is: <strong>{voting_token}</strong></p>
                <!-- rest of your email template -->
            </body>
            </html>
            """

            email_sent = email_handler.send_email(to_email=email, subject='Your Voting Registration Token',
                                                  body=email_html, provider='gmail')

            if email_sent:
                flash('Registration successful! Check your email for your voting token.', 'success')
                return redirect(url_for('registration_confirmation'))
            else:
                flash('Registration completed but email delivery failed. Please contact support.', 'warning')
                return redirect(url_for('register'))

        except Exception as e:
            print(f"Registration error: {str(e)}")
            flash('Registration error occurred. Please try again.', 'error')
            return redirect(url_for('register'))

            # Your registration logic
            session.pop('registration_messages', None)

    return render_template('register.html')


@app.route('/registration_confirmation')
def registration_confirmation():
    return render_template('registration_confirmation.html')


@app.route('/logout_and_redirect')
def logout_and_redirect():
    # Clear session
    session.clear()
    # Mark voter as has_voted in database
    voter_id = session.get('voter_id')
    db.voters.update_one(
        {'_id': voter_id},
        {'$set': {'has_voted': True}}
    )
    return redirect(url_for('index'))

def is_voting_period_active(election):
    current_time = datetime.now()
    early_voting_start = datetime.strptime(election['early_voting_start'], '%Y-%m-%dT%H:%M:%S')
    early_voting_end = datetime.strptime(election['early_voting_end'], '%Y-%m-%dT%H:%M:%S')
    election_start = datetime.strptime(election['election_date_start'], '%Y-%m-%dT%H:%M:%S')
    election_end = datetime.strptime(election['election_date_end'], '%Y-%m-%dT%H:%M:%S')

    # Check if current time falls within early voting or election day period
    is_early_voting = early_voting_start <= current_time <= early_voting_end
    is_election_day = election_start <= current_time <= election_end

    return is_early_voting or is_election_day


@app.route('/castevote', methods=['GET', 'POST'])
def castevote():
    if request.method == 'GET':
        return render_template('castevote.html')

    voting_period = None
    current_time = datetime.now()
    logging.info(f"Current Time: {current_time}")

    # Process voter credentials first
    email = request.form['email'].lower().strip()
    ssn = request.form['ssn'].strip()
    voting_token = request.form['voting_token'].strip()

    # 1. Check if voter is registered
    registered_voter = db.voters.find_one({'email': email, 'SSN': ssn})
    if not registered_voter:
        flash('Voter Registration Required: This email and SSN combination is not registered in our system. Please complete registration first.', 'error')
        logging.warning(f"Unregistered voter attempt: {email}")
        return render_template('castevote.html')

    # 2. Check active elections
    active_elections = list(db.elections.find({'status': 'active'}))
    for election in active_elections:
        early_start = datetime.strptime(election['early_voting_start'], '%Y-%m-%dT%H:%M:%S')
        early_end = datetime.strptime(election['early_voting_end'], '%Y-%m-%dT%H:%M:%S')
        election_start = datetime.strptime(election['election_date_start'], '%Y-%m-%dT%H:%M:%S')
        election_end = datetime.strptime(election['election_date_end'], '%Y-%m-%dT%H:%M:%S')

        logging.info(f"""
            Election: {election['position']}
            Early Voting: {early_start} to {early_end}
            Election Day: {election_start} to {election_end}
            Current Time: {current_time}
            Early Voting Active: {early_start <= current_time <= early_end}
            Election Day Active: {election_start <= current_time <= election_end}
            """)

        if (early_start <= current_time <= early_end) or (election_start <= current_time <= election_end):
            voting_period = election
            break

    if not voting_period:
        next_election = db.elections.find_one({'status': 'upcoming'}, sort=[('early_voting_start', 1)])
        if next_election:
            start_date = datetime.strptime(next_election['early_voting_start'], '%Y-%m-%dT%H:%M:%S')
            flash(f'No Active Election: The next voting period begins {start_date.strftime("%B %d, %Y at %I:%M %p")}', 'warning')
        else:
            flash('No Active Election: Please check back later for upcoming elections.', 'warning')
        return render_template('castevote.html')

    # 3. Check token expiration
    token_expiration = registered_voter.get('token_expiration')
    if not token_expiration or (isinstance(token_expiration, datetime) and token_expiration < current_time):
        flash('Already Voted: Your vote has been recorded for this election. Each voter may only vote once', 'error')
        logging.info(f"Expired token detected for: {email}")
        return render_template('castevote.html')

    # 4. Check if already voted
    if registered_voter.get('has_voted', False):
        flash('Already Voted: Your vote has been recorded for this election. Each voter may only vote once.', 'info')
        logging.info(f"Returning voter detected: {email}")
        return render_template('castevote.html')

    # Final validation of all credentials
    voter = db.voters.find_one({
        'email': email,
        'SSN': ssn,
        'voting_token': voting_token,
        'token_expiration': {'$gt': current_time},
        'status': 'active',
        'has_voted': False
    })

    if voter:
        session['voter_id'] = str(voter['_id'])
        session['validated'] = True
        session['voter_state'] = voter.get('state')
        session['election_id'] = str(voting_period['_id'])

        logging.info(f"Voter validated successfully: {email}")
        flash('Success: Your credentials are verified. Proceeding to your ballot.', 'success')

        db.voters.update_one(
            {'_id': voter['_id']},
            {'$set': {'last_login': current_time}}
        )

        return redirect(url_for('ballot'))

    flash('Invalid Credentials: The provided voting token does not match our records. Please verify and try again.', 'error')
    logging.warning(f"Invalid credentials for: {email}")
    return render_template('castevote.html')


def get_demographic_breakdown(votes):
    demographics = {
        'gender': {},
        'ethnicity': {},
        'age': {}
    }

    for vote in votes:
        demo_data = vote.get('demographics', {})

        # Process gender data
        gender = demo_data.get('gender', 'Not Specified')
        demographics['gender'][gender] = demographics['gender'].get(gender, 0) + 1

        # Process ethnicity data
        ethnicity = demo_data.get('ethnicity', 'Not Specified')
        demographics['ethnicity'][ethnicity] = demographics['ethnicity'].get(ethnicity, 0) + 1

        # Process age data
        age = demo_data.get('age')
        if age:
            age_group = get_age_group(age)
            demographics['age'][age_group] = demographics['age'].get(age_group, 0) + 1

    return demographics


def get_position_category(position):
    categories = {
        'President': 'Executive',
        'Vice President': 'Executive',
        'Senator': 'State',
        'Representative': 'Congressional',
        'Governor': 'State',
        'State Senator': 'State',
        'State Representative': 'State'
    }
    return categories.get(position, 'Other')


@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/candidate', methods=['GET', 'POST'])
def candidate():
    try:
        elections = list(db.elections.find({'status': 'active'}).sort('created_at', -1))

        # Format dates for display
        for election in elections:
            for date_field in ['early_voting_start', 'early_voting_end', 'election_date_start', 'election_date_end']:
                parsed_date = parser.parse(election[date_field])
                election[date_field] = parsed_date.strftime('%m/%d/%Y %I:%M %p')

        app.logger.info(f"Found {len(elections)} active elections")
        current_election = elections[0] if elections else None

        if request.method == 'POST':
            try:
                election_id = request.form.get('election_id')
                if not election_id:
                    flash("Please select an election before registering a candidate.", 'warning')
                    return render_template('candidate.html', elections=elections, election=current_election)

                election = db.elections.find_one({'_id': ObjectId(election_id)})
                if not election:
                    flash("Selected election not found in database. Please try again.", 'error')
                    return render_template('candidate.html', elections=elections, election=current_election)

                # Photo handling
                photo_filename = None
                if 'photo' in request.files:
                    photo = request.files['photo']
                    if photo.filename:
                        photo_filename = secure_filename(photo.filename)
                        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                        photo.save(photo_path)
                        app.logger.debug(f"Photo saved: {photo_path}")

                # Base candidate data
                candidate_data = {
                    'first_name': request.form.get('first_name'),
                    'last_name': request.form.get('last_name'),
                    'category': election.get('category'),
                    'position': election.get('position'),
                    'political_party': request.form.get('political_party'),
                    'state': request.form.get('state'),
                    'email': request.form.get('email'),
                    'phone': request.form.get('phone'),
                    'dob': request.form.get('dob'),
                    'profile_link': request.form.get('profile_link'),
                    'election_id': ObjectId(election_id),
                    'created_at': datetime.now(UTC)
                }

                # Process election dates
                date_fields = ['early_voting_start', 'early_voting_end', 'election_date_start', 'election_date_end']
                for field in date_fields:
                    parsed_date = parser.parse(election[field])
                    candidate_data[field] = parsed_date.isoformat()

                if photo_filename:
                    candidate_data.update({
                        'photo_path': f'uploads/candidates/{photo_filename}',
                        'photo_url': url_for('static', filename=f'uploads/candidates/{photo_filename}', _external=True)
                    })

                result = db.candidates.insert_one(candidate_data)
                if result.inserted_id:
                    session['new_candidate_id'] = str(result.inserted_id)
                    flash('Candidate registered successfully!', 'success')
                    app.logger.info(f"Candidate registered: {result.inserted_id}")
                    return render_template('candidate.html', elections=elections, election=current_election, success=True)
                else:
                    raise ValueError("Failed to insert candidate into database")

            except Exception as e:
                app.logger.error(f"POST Error: {str(e)}", exc_info=True)
                flash(f'Error: {str(e)}', 'error')
                try:
                    admin_candidate_url = url_for('admin_candidates')
                except BuildError:
                    admin_candidate_url = '#'
                    app.logger.warning("Could not build URL for admin_candidate. Using fallback.")
                return render_template('candidate.html', elections=elections, election=current_election, admin_candidate_url=admin_candidate_url)

        return render_template('candidate.html', elections=elections, election=current_election)

    except Exception as e:
        app.logger.error(f"Error in candidate route: {str(e)}")
        flash("An error occurred while processing your request.", "error")
        return render_template('candidate.html', elections=[], election=None)

@app.route('/admin/edit-candidates')
def admin_edit_candidates():
    candidates = db.candidates.find()
    elections = db.elections.find({'status': 'active'})
    return render_template('admin/edit_candidates.html', candidates=candidates, elections=list(elections))


@app.route('/admin/candidates/<candidate_id>', methods=['DELETE'])
def delete_candidate(candidate_id):
    try:
        # Get candidate info before deletion
        candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})

        if candidate:
            candidate_name = f"{candidate['first_name']} {candidate['last_name']}"
            position = candidate['position']

            # Delete from all collections
            db.candidates.delete_one({'_id': ObjectId(candidate_id)})
            db.ballot.delete_many({'candidate_id': ObjectId(candidate_id)})
            db.election_results.delete_many({'candidate_id': ObjectId(candidate_id)})
            db.votes.delete_many({
                '$or': [
                    {'candidate_name': candidate_name},
                    {'position': position}
                ]
            })

            # Clean up any other related collections
            db.stats.delete_many({'candidate_id': ObjectId(candidate_id)})

            return jsonify({
                'success': True,
                'message': 'Candidate and all related data deleted successfully',
                'deleted_candidate': candidate_name
            }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting candidate: {str(e)}'
        }), 500

def calculate_category_stats(votes, category):
    stats = {}
    total_votes = len(votes)

    # Count occurrences of each value in the category
    category_counts = {}
    for vote in votes:
        value = vote.get(category, 'Unknown')
        category_counts[value] = category_counts.get(value, 0) + 1

    # Calculate percentages
    for value, count in category_counts.items():
        percentage = (count / total_votes * 100) if total_votes > 0 else 0
        stats[value] = {
            'count': count,
            'percentage': round(percentage, 2)
        }

    return stats


def calculate_stats(votes, category, is_collective):
    # Count occurrences of each value
    values = {}
    for vote in votes:
        value = vote.get(category, 'Unknown')
        values[value] = values.get(value, 0) + 1

    # Prepare data for plotting
    labels = list(values.keys())
    counts = list(values.values())

    # Create the chart data
    chart_data = [{
        'values': counts,
        'labels': labels,
        'type': 'pie'
    }]

    return json.dumps(chart_data)


@app.route('/refresh-stats')
def refresh_stats():
    # Get fresh data from MongoDB
    votes = list(db.votes.find())

    # Get unique positions that currently exist in votes
    existing_positions = list(set(vote['position'] for vote in votes if 'position' in vote))

    # Clean up any votes with deleted positions
    mongo.db.votes.delete_many({'position': {'$nin': existing_positions}})

    collective_categories = ['race', 'gender', 'education']
    voting_categories = ['position', 'party']
    target_states = ['TX', 'FL', 'NY', 'CA', 'IL']

    # Calculate fresh statistics
    charts = {}
    for category in collective_categories:
        charts[category] = calculate_stats(votes, category, True)
    for category in voting_categories:
        charts[category] = calculate_stats(votes, category, False)

    state_charts = {}
    for state in target_states:
        state_charts[state] = {}
        # Add safe state filtering
        state_votes = [vote for vote in votes if vote.get('state', '').upper() == state]
        for category in collective_categories:
            state_charts[state][category] = calculate_stats(state_votes, category, True)
        for category in voting_categories:
            state_charts[state][category] = calculate_stats(state_votes, category, False)

    category_stats = {}
    for category in collective_categories + voting_categories:
        category_stats[f'{category}_stats'] = calculate_category_stats(votes, category)

    state_category_stats = {}
    for state in target_states:
        state_category_stats[state] = {}
        # Add safe state filtering
        state_votes = [vote for vote in votes if vote.get('state', '').upper() == state]
        for category in collective_categories + voting_categories:
            state_category_stats[state][f'{category}_stats'] = calculate_category_stats(state_votes, category)

    return jsonify({
        'charts': charts,
        'state_charts': state_charts,
        'category_data': {
            'overall': category_stats,
            **state_category_stats
        }
    })


@app.route('/admin_candidates/<candidate_id>', methods=['GET', 'POST'])
def admin_candidate(candidate_id):
    candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})

    if request.method == 'POST':
        # Create comprehensive update data
        update_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'position': request.form.get('position'),
            'political_party': request.form.get('political_party'),
            'state': request.form.get('state'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'dob': request.form.get('dob'),
            'profile_link': request.form.get('profile_link'),
            'category': candidate['category'],
            'election_id': candidate['election_id'],
            'early_voting_start': request.form.get('early_voting_start'),
            'early_voting_end': request.form.get('early_voting_end'),
            'election_date_start': request.form.get('election_date_start'),
            'election_date_end': request.form.get('election_date_end'),
            'created_at': candidate['created_at'],
            'last_updated': datetime.now(timezone.utc)
        }

        # Handle photo upload
        if request.files.get('photo'):
            photo = request.files['photo']
            if photo.filename:
                filename = secure_filename(photo.filename)
                photo_path = os.path.join('uploads', 'candidates', filename)
                full_path = os.path.join(app.static_folder, photo_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                photo.save(full_path)
                update_data['photo_path'] = photo_path
                update_data['photo_url'] = f"/static/{photo_path}"

        try:
            # Update all collections
            result = db.candidates.update_one(
                {'_id': ObjectId(candidate_id)},
                {'$set': update_data}
            )

            if result.modified_count > 0:
                db.ballot.update_many(
                    {'candidate_id': ObjectId(candidate_id)},
                    {'$set': update_data}
                )
                db.election_results.update_many(
                    {'candidate_id': ObjectId(candidate_id)},
                    {'$set': update_data}
                )

                app.logger.info(f"Successfully updated candidate {candidate_id}")
                flash('Candidate updated successfully!', 'success')

                # Fetch fresh candidate data
                candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})
                return render_template('admin/edit_candidate.html', candidate=candidate)
            else:
                flash('No changes were made', 'info')
        except Exception as e:
            app.logger.error(f"Error updating candidate {candidate_id}: {str(e)}")
            flash('Update failed. Please try again.', 'error')

    return render_template('admin/edit_candidate.html', candidate=candidate)


def save_photo(photo):
    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        photo.save(upload_path)
        return {
            'photo_path': f'uploads/candidates/{unique_filename}',
            'photo_url': f'/uploads/candidates/{unique_filename}'  # Right here!
        }
    return None


@app.route('/candidate_details/<candidate_id>')
def candidate_details(candidate_id):
    voter_state = session.get('voter_state')
    candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})

    if not candidate:
        flash('Candidate not found', 'error')
        return redirect(url_for('ballot'))

    election = db.elections.find_one({'_id': ObjectId(candidate.get('election_id'))})

    if not election:
        flash('Election not found', 'error')
        return redirect(url_for('ballot'))

    query = {
        '$or': [
            {'state': voter_state},
            {'state': 'National'}
        ]
    }
    all_candidates = list(db.candidates.find(query))

    organized_candidates = {
        'executive': {},
        'legislative': {},
        'other': {}
    }

    positions = {}

    for c in all_candidates:
        branch = c.get('branch', 'other')
        position = c.get('position', '')
        state = c.get('state', '')

        if state == 'National' or state == voter_state:
            if position not in organized_candidates[branch]:
                organized_candidates[branch][position] = []
            organized_candidates[branch][position].append(c)

            if position not in positions:
                positions[position] = []
            positions[position].append(c)

    image_path = url_for('static', filename=f'images/candidates/{candidate.get("photo")}') if candidate.get(
        'photo') else url_for('static', filename='images/default_candidate.png')

    candidate_info = {
        'name': f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}",
        'party': candidate.get('political_party', ''),
        'position': candidate.get('position', ''),
        'state': candidate.get('state', ''),
        'email': candidate.get('email', ''),
        'image_url': image_path,
        'profile_link': candidate.get('profile_link', '')
    }

    return render_template('ballot.html',
                           candidate=candidate_info,
                           organized_candidates=organized_candidates,
                           election=election, positions=positions)


@app.route('/ballot')
def ballot():
    try:

        voter_state = session.get('voter_state')
        voter_id = session.get('voter_id')

        if not voter_state or not voter_id:
            flash('Voter information not found. Please complete the validation process.', 'error')
            return redirect(url_for('login'))

        # Get voter info for demographics
        voter_info = db.voters.find_one({'_id': ObjectId(voter_id)})

        # Get all active positions
        positions = list(db.elections.distinct('position', {'status': 'active'}))

        if not positions:
            flash('No active positions found for voting.', 'info')
            return redirect(url_for('index'))

        # Get candidates grouped by position and state
        candidates_by_position = {}
        for position in positions:
            candidates = list(db.candidates.find({
                'position': position,
                '$or': [
                    {'state': voter_state},
                    {'state': 'National'}
                ]
            }))

            if candidates:
                candidates_by_position[position] = candidates
            else:
                app.logger.warning(f"No candidates found for position: {position}")

        if not candidates_by_position:
            flash('No candidates found for your state. Please try again later.', 'warning')
            return redirect(url_for('index'))

        app.logger.info(f"Ballot loaded for voter from state: {voter_state}")
        return render_template('ballot.html',
                               positions=positions,
                               candidates=candidates_by_position,
                               voter_info=voter_info)

    except Exception as e:
        app.logger.error(f"Ballot Error: {str(e)}", exc_info=True)
        flash('Error loading ballot. Please try again later.', 'error')
        return redirect(url_for('index'))


@app.route('/submit_to_ballot/<candidate_id>', methods=['POST'])
def submit_to_ballot(candidate_id):
    # Get updated candidate information
    candidate = mongo.db.candidates.find_one({'_id': ObjectId(candidate_id)})

    # Update or insert into ballot collection
    mongo.db.ballot.update_one(
        {'candidate_id': ObjectId(candidate_id)},
        {'$set': {
            'candidate_id': ObjectId(candidate_id),
            'election_id': candidate['election_id'],
            'status': 'active',
            'last_updated': datetime.now()
        }},
        upsert=True
    )

    return jsonify({'success': True, 'message': 'Ballot updated successfully'})


def gather_voter_stats():
    """Gather voter statistics from the database"""
    stats = {
        'total_votes': db.votes.count_documents({}),
        'votes_by_position': {},
        'votes_by_party': {},
        'votes_by_demographics': {
            'gender': {},
            'ethnicity': {},
            'age': {},
            'state': {}
        }
    }

    # Gather votes by position and party
    for vote in db.votes.find():
        position = vote['position']
        party = vote['candidate_party']

        stats['votes_by_position'][position] = stats['votes_by_position'].get(position, 0) + 1
        stats['votes_by_party'][party] = stats['votes_by_party'].get(party, 0) + 1

        # Gather votes by demographics
        for demo_key, demo_value in vote['demographics'].items():
            if demo_value != 'Not Specified':
                stats['votes_by_demographics'][demo_key][demo_value] = stats['votes_by_demographics'][demo_key].get(
                    demo_value, 0) + 1

    return stats


def calculate_age(dob_str):
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        today = datetime.today()
        age = today.year - dob.year
        return str(age)
    except:
        return 'Not Specified'

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    try:
        voter_id = session.get('voter_id')
        if not voter_id:
            flash('Please log in to vote', 'error')
            return redirect(url_for('login'))

        voter_info = db.voters.find_one({'_id': ObjectId(voter_id)})
        if not voter_info:
            raise ValueError("Voter not found")

        if voter_info.get('has_voted', False):
            flash('You have already voted. Thank you for your participation!', 'info')
            session.clear()
            return redirect(url_for('index'))

        demographics = {
            'gender': voter_info.get('gender', 'Not Specified'),
            'ethnicity': voter_info.get('ethnicity', 'Not Specified'),
            'age': calculate_age(voter_info.get('DOB')),
            'state': voter_info.get('state', 'Not Specified'),
        }

        vote_data = {position: {'id': candidate_id} for position, candidate_id in request.form.items()}

        if not vote_data:
            flash("Please select candidates before submitting your vote", 'error')
            return redirect(url_for('ballot'))

        for position, candidate in vote_data.items():
            candidate_id = candidate.get('id')
            if not candidate_id:
                flash(f"Please select a candidate for {position}", 'error')
                return redirect(url_for('ballot'))

            candidate_info = db.candidates.find_one({'_id': ObjectId(candidate_id)})
            if not candidate_info:
                flash(f"Selected candidate for {position} is not valid", 'error')
                return redirect(url_for('ballot'))

            vote_record = {
                'voter_id': ObjectId(voter_id),
                'candidate_id': ObjectId(candidate_id),
                'position': position,
                'demographics': demographics,
                'candidate_party': candidate_info.get('political_party', 'Not Specified'),
                'candidate_name': f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip(),
                'timestamp': datetime.utcnow()
            }
            db.votes.insert_one(vote_record)

        stats = gather_voter_stats()
        db.statistics.update_one({}, {"$set": stats}, upsert=True)

        update_result = db.voters.update_one(
            {'_id': ObjectId(voter_id)},
            {
                '$set': {
                    'has_voted': True,
                    'vote_timestamp': datetime.utcnow(),
                    'voting_token': None,
                    'token_expiration': None
                }
            }
        )

        if update_result.modified_count == 1:
            session.clear()
            flash('Your vote has been successfully recorded! Thank you for participating in this election.', 'success')
            app.logger.info(f"Vote cast successfully for voter {voter_id}")
            return redirect(url_for('vote_success'))
        else:
            raise ValueError("Failed to update voter status")

    except Exception as e:
        app.logger.error(f"Error casting vote: {str(e)}")
        flash("We encountered an issue while processing your vote. Please try again.", 'error')
        return redirect(url_for('ballot'))

@app.route('/vote_success')
def vote_success():
    messages = get_flashed_messages(with_categories=True)
    return render_template('vote_success.html', success=True, messages=messages)


def cleanup_invalid_votes():
    valid_positions = [doc['position'] for doc in db.candidates.find({}, {'position': 1})]
    valid_candidate_names = [f"{doc['first_name']} {doc['last_name']}" for doc in db.candidates.find()]

    # Remove votes with invalid positions or candidates
    db.votes.delete_many({
        '$or': [
            {'position': {'$nin': valid_positions}},
            {'candidate_name': {'$nin': valid_candidate_names}}
        ]
    })

@app.route('/stats')
def stats():
    try:
        # Get valid positions from candidates collection
        valid_positions = [doc['position'] for doc in db.candidates.find({}, {'position': 1})]

        # Clean up votes with invalid positions
        db.votes.delete_many({'position': {'$nin': valid_positions}})

        # Get fresh data after cleanup
        all_votes = list(db.votes.find())

        if not all_votes:
            return jsonify({"success": False, "message": "No votes found in the database"}), 404

        collective_categories = ['state', 'gender', 'age', 'ethnicity']
        voting_categories = ['position', 'candidate_name', 'candidate_party']
        stats_data = {
            **{category: calculate_stats(all_votes, category, True) for category in collective_categories},
            **{category: calculate_stats(all_votes, category, False) for category in voting_categories}
        }

        target_states = ['Texas', 'California', 'Illinois', 'New York', 'Florida']
        state_demographics = {
            state: {
                category: calculate_stats(
                    [vote for vote in all_votes if vote.get('demographics', {}).get('state') == state],
                    category,
                    category in collective_categories
                )
                for category in collective_categories + voting_categories
            }
            for state in target_states
        }

        charts = {category: create_pie_chart(stats_data[category], category) for category in
                 collective_categories + voting_categories}

        state_charts = {
            state: {
                category: create_pie_chart(state_demographics[state][category], f"{state} - {category}")
                for category in collective_categories + voting_categories
            }
            for state in target_states
        }

        # Pass category_stats separately to the template
        category_stats = {f'{category}_stats': stats_data.get(category, {}) for category in
                        collective_categories + voting_categories}

        # Create state_category_stats
        state_category_stats = {
            state: {
                f'{category}_stats': state_demographics[state][category]
                for category in collective_categories + voting_categories
            }
            for state in target_states
        }

        return render_template('stats.html',
                             stats=stats_data,
                             charts=charts,
                             collective_categories=collective_categories,
                             voting_categories=voting_categories,
                             state_demographics=state_demographics,
                             state_charts=state_charts,
                             target_states=target_states,
                             category_stats=category_stats,
                             state_category_stats=state_category_stats)
    except Exception as e:
        app.logger.error(f"Error in stats route: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "An error occurred while fetching statistics"}), 500


def calculate_stats(votes, category, is_collective):
    stats = defaultdict(int)
    total_votes = len(votes)
    counted_voters = set()

    for vote in votes:
        voter_id = str(vote.get('voter_id', 'Unknown'))

        if is_collective:
            if voter_id not in counted_voters:
                # Count demographic info only once per voter
                if category == 'age':
                    value = get_age_group(vote.get('demographics', {}).get('age', 'Not Specified'))
                else:
                    value = vote.get('demographics', {}).get(category, 'Not Specified')

                if value is None or value == '':
                    value = 'Not Specified'

                stats[value] += 1
                counted_voters.add(voter_id)
        else:
            # Count these for each vote
            value = vote.get(category, 'Not Specified')
            if value is None or value == '':
                value = 'Not Specified'
            stats[value] += 1

    # Calculate percentages
    total_count = sum(stats.values())
    return {
        key: {
            'count': count,
            'percentage': round((count / total_count) * 100, 2) if total_count > 0 else 0
        }
        for key, count in stats.items()
    }


def create_pie_chart(data, title):
    labels = list(data.keys())
    values = [item['count'] for item in data.values()]

    trace = go.Pie(labels=labels, values=values, hole=.3)
    layout = go.Layout(title=f'{title.capitalize()} Distribution')
    fig = go.Figure(data=[trace], layout=layout)

    return plotly.utils.PlotlyJSONEncoder().encode(fig)


# Helper function for age groups
def get_age_group(age):
    if not age or age == 'Not Specified':
        return 'Not Specified'
    try:
        age_num = int(age)
        if age_num < 25:
            return '18-24'
        elif age_num < 35:
            return '25-34'
        elif age_num < 50:
            return '35-49'
        elif age_num < 65:
            return '50-64'
        return '65+'
    except ValueError:
        return 'Not Specified'


def gather_voter_stats():
    all_votes = list(db.votes.find())
    total_votes = len(all_votes)

    collective_categories = ['state', 'gender', 'age', 'ethnicity']
    voting_categories = ['position', 'candidate_name', 'candidate_party']

    stats = {
        'total_votes': total_votes,
        **{category: calculate_stats(all_votes, category, True) for category in collective_categories},
        **{category: calculate_stats(all_votes, category, False) for category in voting_categories}
    }

    return stats


# Helper function to calculate age
def calculate_age(dob):
    if not dob:
        return 'Not Specified'
    try:
        birth_date = datetime.strptime(dob, '%Y-%m-%d')
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return str(age)
    except ValueError:
        return 'Not Specified'


if __name__ == '__main__':
    app.run(debug=True)
