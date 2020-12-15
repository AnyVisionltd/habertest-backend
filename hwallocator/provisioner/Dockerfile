FROM python:3.6.9-alpine3.9

RUN apk add --no-cache \
        build-base==0.5-r1
RUN echo 'manylinux1_compatible = True' > /usr/local/lib/python3.6/site-packages/_manylinux.py

RUN pip3 install \
        pipenv==2018.11.26
COPY Pipfile /src/Pipfile
WORKDIR /src
RUN pipenv lock && pipenv install --dev --system
RUN apk del build-base && \
    pip3 uninstall -y pipenv

COPY . /src/

EXPOSE 8080
CMD ["python", "-m", "webapp.app", "serve"]
