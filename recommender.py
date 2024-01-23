# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template,request,redirect,url_for,flash
from flask_user import login_required, UserManager,current_user
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from models import db, User, Movie, MovieGenre, MovieRating, MovieLink
from read_data import check_and_read_data
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix
import pandas as pd
import time

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///movie_recommender.sqlite'  # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Avoids SQLAlchemy warning

    # Flask-User settings
    USER_APP_NAME = "Movie Recommender"  # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False  # Disable email authentication
    USER_ENABLE_USERNAME = True  # Enable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = True  # Simplify register form

def pad_zero(value):
    value=str(value)
    return value.zfill(7) if len(value) < 7 else value

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db
app.jinja_env.filters['pad_zero'] = pad_zero
db.init_app(app)  # initialize database
db.create_all()  # create database if necessary
user_manager = UserManager(app, db, User)  # initialize Flask-User management


@app.cli.command('initdb')
def initdb_command():
    global db
    """Creates the database tables."""
    check_and_read_data(db)
    print('Initialized the database.')


# The Home page is accessible to anyone
@app.route('/')
def home_page():
    # render home.html template
    return render_template("home.html")


# The Members page is only accessible to authenticated users via the @login_required decorator
@app.route('/movies')
@login_required  # User must be authenticated

def movies_page():
    # get rating filter input
    selected_rating = request.args.get('rating')
    # get genre filter input
    selected_genre = request.args.get('genre')
    query = request.args.get('query')
    # Fetch all movies or filtered movies based on genre
    if selected_genre:
        movies_query = Movie.query.filter(Movie.genres.any(MovieGenre.genre == selected_genre))
    else:
        movies_query = Movie.query
    
    if query:
        movies_query = Movie.query.filter(Movie.title.ilike(f'%{query}%'))

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Set the number of movies per page
    paginated_movies = movies_query.paginate(page=page, per_page=per_page, error_out=False)
    movies = paginated_movies.items

    # Fetch user ratings for the displayed movies
    user_ratings = MovieRating.query.filter(
        MovieRating.movie_id.in_([movie.id for movie in movies]),
        MovieRating.user_id == current_user.id
    ).all()

    # fetch distinct genres
    distinct_genres = db.session.query(MovieGenre.genre).distinct().all()
    genre_options = [genre[0] for genre in distinct_genres]
    
    # Create a dictionary to store user ratings for each movie
    user_ratings_dict = {rating.movie_id: rating.rating for rating in user_ratings}

    return render_template("movies.html", 
                           movies=movies, 
                           genre_options=genre_options, 
                           selected_genre=selected_genre, 
                           selected_rating=selected_rating,
                           user_ratings=user_ratings_dict,
                           pagination=paginated_movies,
                           query=query)

@app.route('/rate_movie/<int:movie_id>', methods=['POST'])
def rate_movie(movie_id):
    # Retrieve the user's rating from the form
    user_rating = request.form.get('user_rating')

    # Check if the user has already rated the movie
    existing_rating = MovieRating.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()

    try:
        if existing_rating:
            # Update the existing rating
            existing_rating.rating = user_rating
            flash('Rating updated successfully!', 'success')
        else:
            # Create a new Rating instance and add it to the database
            rating = MovieRating(user_id=current_user.id, movie_id=movie_id, rating=user_rating, timestamp=int(time.time()))
            db.session.add(rating)
            flash('Rating submitted successfully!', 'success')
        db.session.commit()

    except IntegrityError as e:
        db.session.rollback()
        flash(f'Error updating rating ({e.orig}). Please try again.', 'danger')

    return redirect(url_for('user_ratings', user_id=current_user.id))

@app.route('/user_ratings/<int:user_id>')
def user_ratings(user_id):
    # Fetch all movies rated by the user with ID user_id
    user_rated_movies = (
        Movie.query
        .join(MovieRating)  # Join the MovieRating table
        .filter(MovieRating.user_id == user_id)
        .add_columns(MovieRating.rating)  # Include the MovieRating.rating in the result
        .all()
    )
    # Render the user ratings page with the fetched data
    return render_template('user_ratings.html', rated_movies=user_rated_movies)


### RECOMMENDER ###

# Example usage in the 'recommendations' route
@app.route('/recommendations')
def recommendations_page():
    # Fetch user ratings and create a user-movie matrix
    user_ratings = MovieRating.query.all()
    user_ratings_df = pd.DataFrame([(rating.user_id, rating.movie_id, rating.rating) for rating in user_ratings],
                                columns=['user_id', 'movie_id', 'rating'])
    user_movie_matrix = pd.pivot_table(user_ratings_df, index='user_id', columns='movie_id', values='rating',fill_value=0)

    # Train a k-NN model on the user-movie matrix
    knn_model = create_knn_model(user_movie_matrix)

    # Get movie recommendations for the current user
    user_id = current_user.id
    recommendations = get_movie_recommendations(user_id, knn_model, user_movie_matrix)
    
    # Fetch detailed movie information for the recommendations
    recommended_movies = Movie.query.options(joinedload(Movie.links), joinedload(Movie.tags)).filter(Movie.id.in_([movie_id for movie_id, _ in recommendations])).all()
    user_ratings = MovieRating.query.filter(
        MovieRating.movie_id.in_([movie.id for movie in recommended_movies]),
        MovieRating.user_id == current_user.id
    ).all()

    user_ratings_dict = {rating.movie_id: rating.rating for rating in user_ratings}

    return render_template("recommendations.html", recommended_movies=recommended_movies,user_ratings=user_ratings_dict)

def create_knn_model(user_movie_matrix):
    # Convert to CSR matrix for memory efficiency
    csr_data = csr_matrix(user_movie_matrix.values)
    knn_model = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=20, n_jobs=-1)
    knn_model.fit(csr_data)
    return knn_model

def get_movie_recommendations(user_id, knn_model, user_movie_matrix, num_recommendations=5):
    # Get the index of the user in the user-movie matrix
    user_index = user_movie_matrix.index.get_loc(user_id)

    # Get the k-nearest neighbors
    distances, indices = knn_model.kneighbors(user_movie_matrix.iloc[user_index, :].values.reshape(1, -1), n_neighbors=num_recommendations + 1)

    # Exclude the user itself from recommendations
    distances = distances.flatten()[1:]
    indices = indices.flatten()[1:]

    # Get movie recommendations
    recommendations = list(zip(user_movie_matrix.index[indices], distances))

    return recommendations

# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)

