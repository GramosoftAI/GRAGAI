https://github.com/andreiramani/pgvector_pgsql_windows
------------------------------------------------------

- ONLY for PostgreSQL v17 - Windows x64
- Stop PostgreSQL using services.msc
- Extract the zip file to your Postgres installed folder, on overwrite dialog option, choose "Yes to all"
- Start PostgreSQL service
- Run query: 
CREATE EXTENSION vector
- Run this query to check if the extension is enable (t):
SELECT extname,extrelocatable,extversion FROM pg_extension where extname='vector'

