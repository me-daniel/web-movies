# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template,request,redirect,url_for,flash
from flask_user import login_required, UserManager,current_user
from sqlalchemy.orm import joinedload
from models import db, User, Movie, MovieGenre, MovieRating, MovieLink,UserRating
from read_data import check_and_read_data

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

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db
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
    filtered_movies=[]
    # get genre filter input
    selected_genre = request.args.get('genre')
    selected_genres = []
    if selected_genre:
        movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre == selected_genre)).all()
    else:
        movies = Movie.query.limit(10).all()
    if selected_rating:
        for movie in movies:
            if movie.average_rating() >= float(selected_rating):
                filtered_movies.append(movie)
    else:
        filtered_movies = movies
    # Fetch user ratings for the displayed movies
    user_ratings = UserRating.query.filter(UserRating.movie_id.in_([movie.id for movie in movies]),
                                           UserRating.user_id == current_user.id).all()
    # fetch distinct genres
    distinct_genres = db.session.query(MovieGenre.genre).distinct().all()
    genre_options = [genre[0] for genre in distinct_genres]

    # Create a dictionary to store user ratings for each movie
    user_ratings_dict = {rating.movie_id: rating.rating for rating in user_ratings}
    # Handle form submissions
    if request.method == 'POST':
        selected_genres = [request.form.get(f'genre{i}') for i in range(1, 4) if request.form.get(f'genre{i}')]

        # Filter movies based on selected genres
        if selected_genres:
            movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre.in_(selected_genres))).all()
                
        else:
            # If no genres are selected, display all movies
            movies = Movie.query.all()
    return render_template("movies.html", 
                           movies=filtered_movies, 
                           genre_options=genre_options, 
                           selected_genre=selected_genre, 
                           selected_rating=selected_rating,
                           user_ratings=user_ratings_dict)


@app.route('/recommendations')
def recommendations_page():
    return render_template("recommendations.html")

@app.route('/rate_movie/<int:movie_id>', methods=['POST'])
def rate_movie(movie_id):
    # Retrieve the user's rating from the form
    user_rating = request.form.get('user_rating')
    print(user_rating)
    # Create a new Rating instance and add it to the database
    rating = UserRating(user_id=current_user.id, movie_id=movie_id, rating=user_rating)
    db.session.add(rating)
    db.session.commit()

    flash('Rating submitted successfully!', 'success')
    return redirect(url_for('user_ratings', user_id=current_user.id))
@app.route('/user_ratings/<int:user_id>')
def user_ratings(user_id):
    # Fetch all movies rated by the user with ID user_id
    user_rated_movies = (
        Movie.query
        .join(UserRating)  # Join the UserRating table
        .filter(UserRating.user_id == current_user.id)
        .add_columns(UserRating.rating)  # Include the UserRating.rating in the result
        .all()
    )
    # Render the user ratings page with the fetched data
    return render_template('user_ratings.html', rated_movies=user_rated_movies)

# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
