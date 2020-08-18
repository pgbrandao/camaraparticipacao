# Base Image
FROM python:3.8.0-buster

WORKDIR /usr/src/app

# set default environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update

# install locales
RUN apt-get install -y locales locales-all

# install psycopg2 
RUN apt-get install -y python3-psycopg2

# Install pyodbc requirements
RUN apt-get install -y python3-dev
RUN apt-get install -y unixodbc-dev

# Add SQL Server ODBC Driver 17
RUN apt-get install -y curl
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17
RUN ACCEPT_EULA=Y apt-get install -y mssql-tools
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile

RUN pip install --upgrade pip 

# Install project dependencies
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

# Copy files
COPY . /usr/src/app/
