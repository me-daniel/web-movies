import csv
from sqlalchemy.exc import IntegrityError
from models import User, Movie, MovieGenre, MovieRating, MovieLink, MovieTag

def check_and_read_data(db):

    # read movies from csv if movie table is empty in db
    if Movie.query.count() == 0:
        with open('data/movies.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        id = row[0]
                        title = row[1]
                        movie = Movie(id=id, title=title)
                        db.session.add(movie)
                        genres = row[2].split('|')  # genres is a list of genres
                        for genre in genres:  # add each genre to the movie_genre table
                            movie_genre = MovieGenre(movie_id=id, genre=genre)
                            db.session.add(movie_genre)
                            db.session.commit()
                    except IntegrityError:
                        print("Ignoring duplicate movie: " + title)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, "movies read")

    # read ratings from csv if movie table is empty in db
    if MovieRating.query.count() == 0:
        with open('data/ratings.csv', newline='', encoding='utf8') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                count = 0
                dummy_user = 0 #User.query.count()+1
                for row in reader:
                    if count > 0:
                        try:
                            user_id = row[0]
                            movie_id = row[1]
                            rating = row[2]
                            timestamp = row[3]
                            movie_rating = MovieRating(user_id = user_id, movie_id=movie_id, rating=rating, timestamp=timestamp)
                            db.session.add(movie_rating)
                            if user_id != dummy_user:
                                user = User(id=user_id)
                                db.session.add(user)
                                dummy_user = user_id
                            db.session.commit()
                        except IntegrityError:
                            print("Ignoring duplicate rating for user:", user_id, "and movie:", movie_id)
                            db.session.rollback()
                            pass
                    count += 1
                    if count % 100 == 0:
                        print(count, "ratings read")

    # read links from csv if movie table is empty in db
    if MovieLink.query.count() == 0:
        with open('data/links.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        movie_id = row[0]
                        imdb_id = row[1]
                        tmdb_id = row[2]
                        movie_link = MovieLink(movie_id=movie_id, imdb_id=imdb_id, tmdb_id=tmdb_id)
                        db.session.add(movie_link)
                        db.session.commit()
                    except IntegrityError:
                        print("Ignoring duplicate imdb link?: " + imdb_id)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, "links read")

    # read tags from csv if movie table is empty in db
    if MovieTag.query.count() == 0:
        with open('data/tags.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        user_id = row[0]
                        movie_id = row[1]
                        tag = row[2]
                        timestamp = row[3]
                        movie_tag = MovieTag(user_id=user_id, movie_id=movie_id, tag=tag, timestamp=timestamp)
                        db.session.add(movie_tag)
                        db.session.commit()
                    except IntegrityError:
                        print("Ignoring duplicate tag for user: " + user_id, "and movie: " + movie_id)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, "tags read")