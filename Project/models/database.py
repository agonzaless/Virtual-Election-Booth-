from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

from app import db


class ElectionDB:
    def __init__(self, db):
        self.db = db

    def create_election(self, position, early_start, early_end, election_start, election_end):
        election = {
            "position": position,
            "early_voting_start": early_start,
            "early_voting_end": early_end,
            "election_date_start": election_start,
            "election_date_end": election_end,
            "candidates": []  # Will store candidate references
        }
        return self.db.elections.insert_one(election)

    def create_candidate(self, election_id, candidate_data):
        candidate = {
            "election_id": ObjectId(election_id),
            "first_name": candidate_data['first_name'],
            "last_name": candidate_data['last_name'],
            "political_party": candidate_data['political_party'],
            "email": candidate_data['email'],
            "phone": candidate_data['phone'],
            "dob": datetime.strptime(candidate_data['dob'], '%d/%m/%Y'),
            "photo_url": candidate_data.get('photo_url'),
            "votes": 0,
            "registration_date": datetime.utcnow()
        }
        result = self.db.candidates.insert_one(candidate)

        # Update election with candidate reference
        self.db.elections.update_one(
            {"_id": ObjectId(election_id)},
            {"$push": {"candidates": result.inserted_id}}
        )
        return result

    # Initialize MongoDB connection
    client = MongoClient('mongodb://localhost:27017')
    db = client.voting_system
    print("Connected to MongoDB:", db.client.server_info())

    # Create indexes for faster queries and unique constraints
    db.voters.create_index('email', unique=True)
    db.voters.create_index('SSN', unique=True)
    db.voters.create_index('voting_token', unique=True)

    class VoterDB:
        @staticmethod
        def create_voter(voter_data):
            return db.voters.insert_one(voter_data)

        @staticmethod
        def find_voter_by_email(email):
            return db.voters.find_one({'email': email})

        @staticmethod
        def verify_voter(email, ssn, token):
            return db.voters.find_one({
                'email': email,
                'SSN': ssn,
                'voting_token': token
            })