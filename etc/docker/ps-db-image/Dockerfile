FROM postgres:10

ENV POSTGIS_MAJOR 2.5
ENV POSTGIS_VERSION 2.5.5+dfsg-1.pgdg90+2
ENV POSTGRES_DB pasportaservo

RUN apt-get update \
    && apt-cache showpkg postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR \
    && apt-get install -y --no-install-recommends \
         postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR=$POSTGIS_VERSION \
         postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR-scripts=$POSTGIS_VERSION \
    && apt-get install -y libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=eo.UTF-8
RUN apt-get install -y locales \
    && sed -i -e "s/# $LANG.*/$LANG UTF-8/" /etc/locale.gen \
    # && echo -e 'LANG="$LANG"' > /etc/default/locale \
    && dpkg-reconfigure --frontend noninteractive locales \
    && update-locale LANG=$LANG \
    && locale -a

RUN mkdir -p /docker-entrypoint-initdb.d
COPY ./initdb-postgis.sh /docker-entrypoint-initdb.d/10_postgis.sh
COPY ./update-postgis.sh /usr/local/bin
