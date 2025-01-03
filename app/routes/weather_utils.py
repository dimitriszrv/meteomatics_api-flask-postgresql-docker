import io
import requests
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

class WeatherUtils:
    def __init__(self,db_auth, api_auth):
        self.db_auth = db_auth
        self.api_auth = api_auth
        self.db_connection()


    # db connection
    def db_connection(self):
        try:
            # connect using sqlalchemy
            # if db not exists, cannot connect
            # connecting only with host, port, user, password
            # and then creating the db
            engine = create_engine(f"postgresql+psycopg2://{self.db_auth["user"]}:{self.db_auth["password"]}@{self.db_auth["host"]}:{self.db_auth["port"]}/{self.db_auth["database"]}")

            with engine.connect() as connection:
                cursor = connection.connection.cursor()
                self.prepare_data(engine, cursor)

        except SQLAlchemyError as e:
            print(f"Error: {e}...")


    # preparation of data
    def prepare_data(self, engine, cursor):
        # get all locations used for measurements
        locations = self.find_locations(engine)
        # get forecasts for each station using metrics
        self.get_forecasts(locations, engine)

    # get all locations and insert them into db table
    def find_locations(self, engine):
        try:
            locations_url = "https://api.meteomatics.com/find_station?source=mm-mos"
            response = requests.get(locations_url, auth=(self.api_auth["user"], self.api_auth["password"]))
            csv_data = io.StringIO(response.text)
            print("Fetching locations...")
            df = pd.read_csv(csv_data, delimiter=";")
            # we need only columns = [Name, Location (Lat, Lon)]
            df = df[["Name", "Location Lat,Lon"]]
            df = df.rename(columns={"Name": "name", "Location Lat,Lon": "lat_lon"})
            # split location coordinates as are: 55.3992,3.8103
            df[['latitude', 'longitude']] = df['lat_lon'].str.split(',', expand=True)
            # convert the new latitude and longitude columns to float type
            df['latitude'] = df['latitude'].astype(float)
            df['longitude'] = df['longitude'].astype(float)
            # drop the original lat_lon column as no longer needed
            df = df.drop(columns=['lat_lon'])
            df = df.drop_duplicates(subset="name")
            df = df.sort_values(by="name")
            # reset df.index, starting with 1
            # this will be used as a primary key at locations table, column id
            df.index = range(1, len(df) + 1)
            # df.to_sql works better with SQLAlchemy
            df.to_sql(name = "locations", con = engine, if_exists = "replace", index = True, index_label = "id", chunksize = 1000)
            df.to_csv("database_data/locations.csv", index_label="id")
            print("Locations fetched successfully...")
            return df
        except requests.exceptions.RequestException as e:
            # this will catch network errors, bad status codes, and invalid JSON
            print(f"An error occurred: {e}")


    # get forecasts for each location
    def get_forecasts(self, df, engine):
        print("Fetching forecasts...")
        forecasts = []
        # split df into chunks as we need lots of requests
        # as locations are 1480
        chunk = 500
        for start in range(0, len(df), chunk):
            # check in case len(df) < chunk
            end = min(start + chunk, len(df))
            # each time keep chunk
            chunked_df = df.iloc[start:end]
            # now in order to request the forecasts, there is a way like merging all locations with +
            # ex 55.3992,3.8103+24.85,-80.6333+50.798,6.024+47.4799,8.90493
            # first concat as "latitude,longitude"
            lat_lon = chunked_df["latitude"].astype(str) + "," + chunked_df["longitude"].astype(str)
            # and finally concat each chunk row using +
            lat_lon = lat_lon.str.cat(sep="+")
            try:
                forecasts_url = f"https://api.meteomatics.com/nowP7D/t_2m:C/{lat_lon}/json"
                response = requests.get(forecasts_url, auth=(self.api_auth["user"], self.api_auth["password"]))
                coordinates_values = response.json()["data"][0]["coordinates"]
                for data in coordinates_values:
                    lat = data["lat"]
                    lon = data["lon"]
                    dates = data["dates"]

                    # foreign key references to locations table, used to extract the index id that references to main df with locations
                    fk_location_id = \
                    chunked_df[(chunked_df["latitude"] == lat) & (chunked_df["longitude"] == lon)].index[0].item()
                    for _ in dates:
                        # split the timestamp into date and time parts
                        date_str, time_str = _["date"].rstrip('Z').split('T')
                        # convert to datetime and time objects
                        date_object = datetime.strptime(date_str, "%Y-%m-%d").date()
                        time_object = datetime.strptime(time_str, "%H:%M:%S").time()
                        forecasts.append([fk_location_id, date_object, time_object, _["value"]])
            except requests.exceptions.RequestException as e:
                # this will catch network errors, bad status codes, and invalid JSON
                print(f"An error occurred: {e}")

        print("Forecasts fetched successfully...")
        final_forecasts = pd.DataFrame(forecasts, columns=["location_id", "date", "time", "temperature"])
        final_forecasts.index = range(1, len(final_forecasts) + 1)
        # df.to_sql works better with SQLAlchemy
        final_forecasts.to_sql(name="forecasts", con=engine, if_exists="replace", index=True, index_label="id", chunksize=1000)
        final_forecasts.to_csv("database_data/forecasts.csv", index_label="id")