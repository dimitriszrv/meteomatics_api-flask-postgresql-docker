import os
import json
import psycopg2

from psycopg2 import Error
from dotenv import load_dotenv
from weather_utils import WeatherUtils
from flask import Flask, g, render_template, request, jsonify

app = Flask(__name__,
            template_folder="../templates",
            static_folder="../static")

load_dotenv(dotenv_path="app/configs/flask.env")

# db config
DATABASE_CONFIG = json.loads(os.getenv("DATABASE_CONFIG"))

# meteomatics_api config
API_CONFIG = json.loads(os.getenv("API_CONFIG"))

# available metrics
# will be used in a future release, to get top_n_locations on each available metric
# API_METRICS = json.loads(os.getenv("API_METRICS"))

# connect to db
def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(**DATABASE_CONFIG)
    return g.db


@app.before_request
def before_request():
    # before every request, connect to the db
    get_db()


@app.teardown_request
def teardown_request(exception):
    # close the db connection after the request is finished
    if request.endpoint != "home":
        db = g.pop("db", None)
        if db is not None:
            db.close()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/locations")
def locations():
    cursor = g.db.cursor()
    cursor.execute("""SELECT id, name 
                        FROM locations
                        ORDER BY id ASC""")
    data = cursor.fetchall()
    return render_template("locations.html", data=data)


@app.route("/latest_forecast")
def latest_forecast():
    cursor = g.db.cursor()
    cursor.execute("""SELECT l.name
                            , f.date
                            , f.time
                            , f.temperature
                        FROM forecasts f
                            INNER JOIN locations l ON l.id = f.location_id
                            ORDER BY f.location_id ASC, f.date ASC, f.time ASC""")
    data = cursor.fetchall()
    return render_template("latest_forecast.html", data=data)


@app.route("/average_temperature")
def average_temperature():
    cursor = g.db.cursor()
    cursor.execute("""WITH last_3 AS (
                            SELECT location_id
                                    , date
                                    , time
                                    , temperature
                                    , RANK() OVER (PARTITION BY location_id, date ORDER BY date DESC, time DESC) AS avg_rank
                            FROM forecasts)
                            , avg_temp AS (
                                SELECT location_id
                                        , date
                                        , round(avg(temperature)::NUMERIC, 2) AS average_temperature
                                FROM last_3
                                WHERE avg_rank <= 3
                                GROUP BY location_id, date)
                            SELECT name
                                    , date
                                    , average_temperature
                            FROM avg_temp
                                INNER JOIN locations ON locations.id = avg_temp.location_id
                                ORDER BY location_id ASC, date ASC""")
    data = cursor.fetchall()
    return render_template("average_temperature.html", data=data)


if __name__ == "__main__":
    try:
        utils = WeatherUtils(DATABASE_CONFIG, API_CONFIG)
    except Exception as e:
        app.logger.error(f"Error initializing WeatherUtils: {e}")
    app.run(host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=True)