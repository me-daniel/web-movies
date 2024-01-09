# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template,request,redirect,url_for
from flask_user import login_required, UserManager

from models import db, User, Movie, MovieGenre,Rating,MovieLink
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
@app.route('/movie_imdb/<int:movie_id>')
def movie_imdb(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    link = MovieLink.query.filter_by(movie_id=movie_id).first()

    if link and link.imdb_id:
        imdb_url = f'https://www.imdb.com/title/{link.imdb_id}/'
        return redirect(imdb_url)
    else:
        # Redirect to a default page if IMDb ID is not available
        return redirect(url_for('default_imdb_page'))

# The Members page is only accessible to authenticated users via the @login_required decorator
@app.route('/movies')
@login_required  # User must be authenticated
def movies_page():
    # String-based templates
    selected_genres = []
    selected_rating = request.args.get('rating')
    # first 10 movies
    selected_genre = request.args.get('genre')

    if selected_genre:
        movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre == selected_genre)).all()
    else:
        movies = Movie.query.limit(10).all()

    # Fetch distinct genres from the database
    distinct_genres = db.session.query(MovieGenre.genre).distinct().all()

    # Convert the result to a list of strings
    genre_options = [genre[0] for genre in distinct_genres]
    # Handle form submissions
    if request.method == 'POST':
        selected_genres = [request.form.get(f'genre{i}') for i in range(1, 4) if request.form.get(f'genre{i}')]

        # Filter movies based on selected genres
        if selected_genres:
            movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre.in_(selected_genres))).all()
        else:
            # If no genres are selected, display all movies
            movies = Movie.query.all()
    for movie in movies:
        ratings_array =[rating.rating for rating in movie.ratings]
    print(ratings_array)

    # Commit the changes to the database
    db.session.commit()
            
    # only Romance movies
    # movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre == 'Romance')).limit(10).all()

    # only Romance AND Horror movies
    # movies = Movie.query\
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Romance')) \
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Horror')) \
    #     .limit(10).all()
    return render_template("movies.html", movies=movies,genre_options=genre_options,selected_genre=selected_genre,selected_rating=selected_rating)


# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
    app.add_url_rule('/movie_imdb/<int:movie_id>', 'movie_imdb', movie_imdb)
