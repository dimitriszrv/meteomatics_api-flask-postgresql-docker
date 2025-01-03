# download python version
FROM python:3.12-alpine3.21

# set work directory
WORKDIR /app

# copy application code into container workdir
COPY /app/ /app/

# upgrade pip to latest version
RUN pip install --upgrade pip

# install requirements
RUN pip install -r configs/requirements.txt

# change permissions
# RUN chmod -R 777 /app/database_data

# expose at port 5000
EXPOSE 5000:5000

# run python app
CMD ["python","routes/weather_api.py"]