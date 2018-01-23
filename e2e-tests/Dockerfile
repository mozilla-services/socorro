FROM python:2.7-alpine
WORKDIR /src
COPY requirements/requirements.txt /src
RUN pip install pipenv
RUN pipenv install --system -r requirements.txt --skip-lock --deploy
COPY . /src
CMD pytest --driver SauceLabs
