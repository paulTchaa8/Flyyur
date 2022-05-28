#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify, abort
from flask_moment import Moment
from models import db, Venue, Artist, Show
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from flask_migrate import Migrate
from datetime import datetime
from forms import *
import os, sys, ast
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)

# TODO: connect to a local postgresql database
migrate = Migrate(app, db)
#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#
# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
	date = dateutil.parser.parse(value)
	if format == 'full':
		format="EEEE MMMM, d, y 'at' h:mma"
	elif format == 'medium':
		format="EE MM, dd, y h:mma"
	
	return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
	return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
	# TODO: replace with real venues data.
	# num_upcoming_shows should be aggregated based on number of upcoming shows per venue.

	data = []

	cities = Venue.query.with_entities(Venue.city, Venue.state).distinct().all()
	for city in cities:
		final = {}
		final["city"] = city[0]
		final["state"] = city[1]
		liste_v = []
		venues = Venue.query.filter_by(city=city[0]).order_by('id')
		for v in venues:
			obj = {}
			obj["id"] = v.id
			obj["name"] = v.name
			# Upcoming shows have startime greather than today..
			obj["num_upcoming_shows"] = Show.query.filter(
				Show.start_time>=datetime.today(), \
				Show.venue_id==v.id).count()
			liste_v.append(obj)
		final["venues"] = liste_v

		data.append(final)

	del cities

	return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
	# TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
	# search for Hop should return "The Musical Hop".
	# search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"

	response = {}
	to_find = request.form.get('search_term', '')
	venues = Venue.query.filter(Venue.name.ilike(f'%{to_find}%')).order_by('id')

	response["count"] = venues.count()
	data = []
	for venue in venues:
		obj = {}
		obj["id"] = venue.id
		obj["name"] = venue.name

		# Upcoming shows have start time greather than today..
		obj["num_upcoming_shows"] = Show.query.filter(
			Show.start_time>=datetime.today(),
			Show.venue_id==venue.id).count()
		data.append(obj)
	response["data"] = data

	return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
	# shows the venue page with the given venue_id
	# TODO: replace with real venue data from the venues table, using venue_id
	data = {}
	error = False
	try:
		
		#Fetch the right venue to be rendered..
		venue = Venue.query.get(venue_id)
		mes_genres = ''.join(venue.genres[1:-1]).split(',')
		mes_genres = [val[1:-1] if val[0] == '"' else val for val in mes_genres]
		data["id"] = venue.id
		data["name"] = venue.name
		data["genres"] = mes_genres
		data["address"] = venue.address
		data["city"] = venue.city
		data["state"] = venue.state
		data["phone"] = venue.phone
		data["website"] = venue.website
		data["facebook_link"] = venue.facebook_link
		data["seeking_talent"] = venue.seeking_talent
		data["seeking_description"] = venue.seeking_description
		data["image_link"] = venue.image_link

		past_shows = db.session.query(Show).join(Venue).filter(
			Show.venue_id==venue_id,
			Show.start_time<datetime.today()
		)
		pasts = []
		for p_show in past_shows:
			obj = {}
			art_id = p_show.artist_id
			artist = Artist.query.get(art_id)
			obj["artist_id"] = artist.id
			obj["artist_name"] = artist.name
			obj["artist_image_link"] = artist.image_link
			obj["start_time"] = str(p_show.start_time)
			pasts.append(obj)
		data["past_shows"] = pasts

		# Idem, fetching upcoming shows for that venue..
		coming_shows = db.session.query(Show).join(Venue).filter(
			Show.venue_id==venue_id,
			Show.start_time>=datetime.today()
		)

		comes = []
		for p_show in coming_shows:
			obj = {}
			art_id = p_show.artist_id
			artist = Artist.query.get(art_id)
			obj["artist_id"] = artist.id
			obj["artist_name"] = artist.name
			obj["artist_image_link"] = artist.image_link
			obj["start_time"] = str(p_show.start_time)
			comes.append(obj)

		data["upcoming_shows"] = comes
		data["past_shows_count"] = len(pasts)
		data["upcoming_shows_count"] = len(comes)
	except:
		error = True

	if error is False:
		return render_template('pages/show_venue.html', venue=data)
	else:
		return redirect(url_for('index'))

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
	form = VenueForm()
	return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
	# TODO: insert form data as a new Venue record in the db, instead
	form = VenueForm()

	if form.validate_on_submit():
		try:
			# Checks if there is such a Venue already stored..
			avenue_old = Venue.query.filter(
				Venue.name.ilike(f"{request.form['name']}"),
				Venue.city.ilike(f"{request.form['city']}")).first()

			if avenue_old is not None:
				flash('An error occurred. Venue ' + request.form['name'] + ' already exists.')
			else:
				# Hooray, new Venue to be stored..
				bodyRequest = request.form
				seek_talent = True if 'seeking_talent' in bodyRequest.keys() else False
				venue = Venue(
					name = bodyRequest['name'],
					city = bodyRequest['city'],
					state = bodyRequest['state'],
					address = bodyRequest['address'],
					phone = bodyRequest['phone'],
					image_link = bodyRequest['image_link'],
					facebook_link = bodyRequest['facebook_link'],
					website = bodyRequest['website_link'],
					seeking_talent = seek_talent,
					seeking_description = bodyRequest['seeking_description'],
					genres = bodyRequest.getlist('genres')
				)
				db.session.add(venue)
				db.session.commit()

				# on successful db insert, flash success..
				flash('Venue ' + request.form['name'] + ' was successfully listed!')

		except Exception as e:
			db.session.rollback()
			print(sys.exc_info())
			# TODO: on unsuccessful db insert, flash an error instead.
			flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.',
				"error")
			# see: http://flask.pocoo.org/docs/1.0/patterns/flashing/

		finally:
			db.session.close()

		return render_template('pages/home.html')
	else:
		for field, message in form.errors.items():
			flash(field + ' - ' + str(message), "error")
			return render_template('forms/new_venue.html', form=form)


@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
	# TODO: Complete this endpoint for taking a venue_id, and using
	# SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
	element = None
	try:
		venue = Venue.query.get(venue_id)
		element = venue.name
		db.session.delete(venue)
		db.session.commit()
		flash(f"{element} deleted !")
	except Exception as e:
		print("Error Venue deletion -> ", e)
		db.session.rollback()
		flash("Unable to delete !")
	finally:
		db.session.close()

	# BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
	# clicking that button delete it from the db then redirect the user to the homepage
	return redirect(url_for('index'))

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
	# TODO: replace with real data returned from querying the database
	data = []

	artists = Artist.query.order_by(db.desc(Artist.id)).all()
	for art in artists:
		obj = {}
		obj["id"] = art.id
		obj["name"] = art.name
		data.append(obj)

	del artists
	return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
	# TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
	# seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
	# search for "band" should return "The Wild Sax Band".
	response = {}
	to_find = request.form.get('search_term', '')
	artists = Artist.query.filter(Artist.name.ilike(f'%{to_find}%')).order_by('id')

	response["count"] = artists.count()
	data = []
	for art in artists:
		obj = {}
		obj["id"] = art.id
		obj["name"] = art.name

		# Upcoming shows have startime greather than today..
		obj["num_upcoming_shows"] = Show.query.filter(
			Show.start_time>=datetime.today(),
			Show.artist_id==art.id).count()
		data.append(obj)
	response["data"] = data

	del to_find, data, artists

	return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
	# shows the artist page with the given artist_id
	# TODO: replace with real artist data from the artist table, using artist_id
	data = {}

	#Fetch the right venue to be rendered..
	artist = Artist.query.get(artist_id)

	mes_genres = ''.join(artist.genres[1:-1]).split(',')
	mes_genres = [val[1:-1] if val[0] == '"' else val for val in mes_genres]

	data["id"] = artist.id
	data["name"] = artist.name
	data["genres"] = mes_genres
	data["city"] = artist.city
	data["state"] = artist.state
	data["phone"] = artist.phone
	data["website"] = artist.website
	data["facebook_link"] = artist.facebook_link
	data["seeking_venue"] = artist.seeking_venue
	data["seeking_description"] = artist.seeking_description
	data["image_link"] = artist.image_link

	past_shows = db.session.query(Show).join(Artist).filter(
		Show.artist_id==artist_id,
		Show.start_time<datetime.today()
	)
	pasts = []
	for p_show in past_shows:
		obj = {}
		ven_id = p_show.venue_id
		venue = Venue.query.get(ven_id)
		obj["venue_id"] = venue.id
		obj["venue_name"] = venue.name
		obj["venue_image_link"] = venue.image_link
		obj["start_time"] = str(p_show.start_time)
		pasts.append(obj)
	data["past_shows"] = pasts

	# Idem, fetching upcoming shows for that artist.
	coming_shows = db.session.query(Show).join(Artist).filter(
		Show.artist_id==artist_id,
		Show.start_time>=datetime.today()
	)
	comes = []
	for p_show in coming_shows:
		obj = {}
		ven_id = p_show.venue_id
		venue = Venue.query.get(ven_id)
		obj["venue_id"] = venue.id
		obj["venue_name"] = venue.name
		obj["venue_image_link"] = venue.image_link
		obj["start_time"] = str(p_show.start_time)
		comes.append(obj)
	data["upcoming_shows"] = comes

	data["past_shows_count"] = len(pasts)
	data["upcoming_shows_count"] = len(comes)

	return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
	form = ArtistForm()

	# TODO: populate form with fields from artist with ID <artist_id>
	artist = {}
	art = Artist.query.get(artist_id)
	artist["id"] = art.id
	artist["name"] = art.name
	artist["genres"] = ''.join(art.genres[1:-1]).split(',')
	artist["city"] = art.city
	artist["state"] = art.state
	artist["phone"] = art.phone
	artist["website"] = art.website
	artist["facebook_link"] = art.facebook_link
	artist["seeking_venue"] = art.seeking_venue
	artist["seeking_description"] = art.seeking_description
	artist["image_link"] = art.image_link
	return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
	# TODO: take values from the form submitted, and update existing
	# artist record with ID <artist_id> using the new attributes
	form = ArtistForm()
	artist = Artist.query.get(artist_id)
	if form.validate_on_submit():
		bodyRequest = request.form
		seeking_venue = True if 'seeking_venue' in bodyRequest.keys() else False

		try:
			artist.name = bodyRequest['name']
			artist.city = bodyRequest['city']
			artist.state = bodyRequest['state']
			artist.phone = bodyRequest['phone']
			artist.genres = bodyRequest.getlist('genres')
			artist.image_link = bodyRequest['image_link']
			artist.facebook_link = bodyRequest['facebook_link']
			artist.website = bodyRequest['website_link']
			artist.seeking_venue = seeking_venue
			artist.seeking_description = bodyRequest['seeking_description']
			db.session.commit()
			flash("Successfully updated !")
		except Exception as e:
			print("Something Wrong -> ", sys.exc_info())
			db.session.rollback()
			flash("Failed to update !")

		finally:
			db.session.close()

		return redirect(url_for('show_artist', artist_id=artist_id))
	else:
		for field, message in form.errors.items():
			flash(field + ' - ' + str(message), 'danger')
		return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
	form = VenueForm()

	# TODO: populate form with values from venue with ID <venue_id>
	venue = {}
	ven = Venue.query.get(venue_id)
	venue["id"] = ven.id
	venue["name"] = ven.name
	venue["genres"] = ''.join(ven.genres[1:-1]).split(',')
	venue["address"] = ven.address
	venue["city"] = ven.city
	venue["state"] = ven.state
	venue["phone"] = ven.phone
	venue["website"] = ven.website
	venue["facebook_link"] = ven.facebook_link
	venue["seeking_talent"] = ven.seeking_talent
	venue["seeking_description"] = ven.seeking_description
	venue["image_link"] = ven.image_link

	return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
	# TODO: take values from the form submitted, and update existing
	# venue record with ID <venue_id> using the new attributes
	form = VenueForm()
	venue = Venue.query.get(venue_id)
	if form.validate_on_submit():
		try:
			bodyRequest = request.form
			seek_talent = True if 'seeking_talent' in bodyRequest.keys() else False

			venue.name = bodyRequest['name']
			venue.city = bodyRequest['city']
			venue.state = bodyRequest['state']
			venue.address = bodyRequest['address']
			venue.phone = bodyRequest['phone']
			venue.image_link = bodyRequest['image_link']
			venue.facebook_link = bodyRequest['facebook_link']
			venue.website = bodyRequest['website_link']
			venue.seeking_talent = seek_talent
			venue.seeking_description = bodyRequest['seeking_description']
			venue.genres = bodyRequest.getlist('genres')
			db.session.commit()
			flash("Successfully updated !")

		except Exception as e:
			print(sys.exc_info())
			db.session.rollback()
			flash("Failed to update !")

		finally:
			db.session.close()
		return redirect(url_for('show_venue', venue_id=venue_id))
	else:
		for field, message in form.errors.items():
			flash(field + ' - ' + str(message), 'warning')
		return render_template('forms/edit_venue.html', form=form, venue=venue)

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
	form = ArtistForm()
	return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
	form = ArtistForm()
	if form.validate_on_submit():
		data = {}
		# called upon submitting the new artist listing form
		try:
			# Finds if there is such an artist already stored..
			artist_old = Artist.query.filter(
				Artist.name.ilike(f"{request.form['name']}")).first()

			if artist_old is not None:
				flash('An error occurred. Artist ' + request.form['name'] + ' already exists.', 'error')
			else:
				bodyRequest = request.form
				seeking_venue = True if 'seeking_venue' in bodyRequest.keys() else False

				artist = Artist(
					name = bodyRequest['name'],
					city = bodyRequest['city'],
					state = bodyRequest['state'],
					phone = bodyRequest['phone'],
					genres = bodyRequest.getlist('genres'),
					image_link = bodyRequest['image_link'],
					facebook_link = bodyRequest['facebook_link'],
					website = bodyRequest['website_link'],
					seeking_venue = seeking_venue,
					seeking_description = bodyRequest['seeking_description']
				)
				db.session.add(artist)
				db.session.commit()
				data['name'] = request.form['name']
				# on successful db insert, flash success
				flash('Artist ' + data['name'] + ' was successfully listed!')

		except Exception as e:
			db.session.rollback()
			print(sys.exc_info())

			# TODO: on unsuccessful db insert, flash an error instead.
			flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')

		finally:
			db.session.close()
		
		# TODO: modify data to be the data object returned from db insertion
		return render_template('pages/home.html')
	else:
		for field, message in form.errors.items():
			flash(field + ' - ' + str(message), 'warning')
			return render_template('forms/new_artist.html', form=form)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
	# displays list of shows at /shows
	# TODO: replace with real venues data.

	data = []
	shows = Show.query.order_by(db.desc(Show.id)).all()

	for show in shows:
		venue = Venue.query.get(show.venue_id)
		artist = Artist.query.get(show.artist_id)
		objet = {}
		objet["venue_id"] = venue.id
		objet["venue_name"] = venue.name
		objet["artist_id"] = artist.id
		objet["artist_name"] = artist.name
		objet["artist_image_link"] = artist.image_link
		objet["start_time"] = str(show.start_time)
		data.append(objet)

	return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
	# renders form. do not touch.
	form = ShowForm()
	return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
	# called to create new shows in the db, upon submitting new show listing form
	# TODO: insert form data as a new Show record in the db, instead
	try:
		old_show = Show.query.filter(
			Show.venue_id==int(request.form['venue_id']),
	        Show.start_time==request.form['start_time']
	    ).count()

		if old_show > 0:
			flash('An error occurred. That Show already exists !')
		else:
			# New show to be listed..
			new_show = Show(
				venue_id=request.form['venue_id'],
				artist_id=request.form['artist_id'],
				start_time=request.form['start_time']
			)
			db.session.add(new_show)
			db.session.commit()
			# on successful db insert, flash success
			flash('Show was successfully listed!')
	except Exception as ev:
		print(sys.exc_info())
		db.session.rollback()
		flash('An error occurred. Show could not be listed.')

	finally:
		db.session.close()

	return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
	return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
	return render_template('errors/500.html'), 500


if not app.debug:
	file_handler = FileHandler('error.log')
	file_handler.setFormatter(
		Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
	)
	app.logger.setLevel(logging.INFO)
	file_handler.setLevel(logging.INFO)
	app.logger.addHandler(file_handler)
	app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
'''
if __name__ == '__main__':
	app.run()
'''

# Or specify port manually:

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5000))
	app.run(host='0.0.0.0', port=port)