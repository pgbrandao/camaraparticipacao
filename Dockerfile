# Base Image
FROM python:3.8.0-alpine

# create and set working directory
# RUN mkdir /app
# WORKDIR /app
WORKDIR /usr/src/app

# Add current directory code to working directory
# ADD . /app/

# set default environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
# ENV LANG C.UTF-8
# ENV DEBIAN_FRONTEND=noninteractive 

RUN apk update

# Install necessary packages
RUN apk add g++ make
RUN apk add gnupg

# install psycopg2 dependencies
RUN apk add postgresql-dev gcc python3-dev musl-dev

# install pyodbc dependencies
RUN apk add unixodbc unixodbc-dev

# Add SQL Server ODBC Driver 17 for Ubuntu 18.04
RUN apk add curl
RUN curl -O https://download.microsoft.com/download/e/4/e/e4e67866-dffd-428c-aac7-8d28ddafb39b/msodbcsql17_17.5.2.2-1_amd64.apk
RUN curl -O https://download.microsoft.com/download/e/4/e/e4e67866-dffd-428c-aac7-8d28ddafb39b/mssql-tools_17.5.2.1-1_amd64.apk
RUN ACCEPT_EULA=Y apk add --allow-untrusted msodbcsql17_17.5.2.2-1_amd64.apk
RUN ACCEPT_EULA=Y apk add --allow-untrusted mssql-tools_17.5.2.1-1_amd64.apk
# RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile
# RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc

# set project environment variables
# grab these via Python's os.environ
# these are 100% optional here
# ENV PORT=8000

# Install system dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#         tzdata \
#         python3-setuptools \
#         python3-pip \
#         python3-dev \
#         python3-venv \
#         git \
#         && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*


# install environment dependencies
RUN pip install --upgrade pip 
# RUN pip3 install pipenv

COPY ./requirements.txt /usr/src/app/requirements.txt

# Install project dependencies
# RUN pipenv install --skip-lock --system --dev
RUN pip install -r requirements.txt

# EXPOSE 8000
# CMD gunicorn camaraparticipacao.wsgi:application --bind 0.0.0.0:$PORT

# COPY requirements.txt /code/
COPY . /usr/src/app/


