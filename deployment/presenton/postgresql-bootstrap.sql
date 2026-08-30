\set ON_ERROR_STOP on

SELECT format('CREATE ROLE presenton LOGIN PASSWORD %L', :'presenton_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'presenton')
\gexec

SELECT 'CREATE DATABASE presenton OWNER presenton'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'presenton')
\gexec

ALTER ROLE presenton NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
REVOKE ALL ON DATABASE presenton FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE presenton TO presenton;
