## Update Server Container (add/update python scripts)

After you added new scripts (or modified them) to `/home/n8n/scripts` folder on the server you need to rebuild python-scripts container `docker compose build python-scripts --no-cache`

then do `docker compose down` and `docker compose up -d` if you want to restart all n8n cluster, 

or do `docker compose stop python-scripts` and `docker compose up -d python-scripts`

then you can check updated scripts in container `docker exec -it n8n-python-scripts-1 bash`