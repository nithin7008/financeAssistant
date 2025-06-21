FROM mysql:8.0

ENV MYSQL_ROOT_PASSWORD=root
ENV MYSQL_DATABASE=testdb
ENV MYSQL_USER=user
ENV MYSQL_PASSWORD=password

COPY init.sql /docker-entrypoint-initdb.d/
