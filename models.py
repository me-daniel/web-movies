from flask_sqlalchemy import SQLAlchemy
from flask_user import UserMixin
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

# Define the User data-model.
# NB: Make sure to add flask_user UserMixin as this adds additional fields and properties required by Flask-User
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')

    # User authentication information. The collation='NOCASE' is required
    # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
    username = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    email_confirmed_at = db.Column(db.DateTime())

    # User information
    first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
    last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')


class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)
    genres = db.relationship('MovieGenre', backref='movie', lazy=True)
    tags = db.relationship('MovieTag', backref='movie', lazy=True)
    links = db.relationship('MovieLink', backref='movie', lazy=True)
    ratings = db.relationship('MovieRating', backref='movie',lazy=True)
    user_ratings=db.relationship('UserRating',backref='movie',lazy=True)

    def average_rating(self):
        ratings = [rating.rating for rating in self.ratings]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        return round(avg_rating, 2)
    
    def unique_tags(self):
        # Extract unique tags using a set comprehension
        return {tag.tag for tag in self.tags}

class MovieGenre(db.Model):
    __tablename__ = 'movie_genres'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    genre = db.Column(db.String(255), nullable=False, server_default='')

class MovieRating(db.Model):
    __tablename__ = 'movie_ratings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.Float, nullable=False)

class MovieLink(db.Model):
    __tablename__ = 'movie_links'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    imdb_id = db.Column(db.Integer, nullable=False)
    tmdb_id = db.Column(db.Integer, nullable=False)

class MovieTag(db.Model):
    __tablename__ = 'movie_tags'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    tag = db.Column(db.String(255), nullable=False, server_default='',unique=True)
    timestamp = db.Column(db.Integer, nullable=False)
class UserRating(db.Model):
    __tablename__ = 'user_ratings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'movie_id', name='_user_movie_uc'),)