# Base Image
FROM python:3.8.0-alpine

WORKDIR /usr/src/app

# set default environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

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

RUN pip install --upgrade pip 

# Install project dependencies
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

# Copy files
COPY . /usr/src/app/
