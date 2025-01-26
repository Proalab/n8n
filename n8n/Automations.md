# Setting up infrastricture for Automations and Scripts

## Automations

Check Python Scripts:

`https://github.com/Proalab/automations`

### Setting up DB

1. Access the PostgreSQL Container

Run the following command to enter the PostgreSQL shell:

`docker exec -it n8n-postgres-1 psql -U root -d n8n`

2. Create the automations Database

In the PostgreSQL shell, run:

`CREATE DATABASE automations;`

3. Verify the Database

After creating the database, you can list all databases to confirm:

`\l`

4. Exit the Shell

Type:

`\q`


### Creating a Table

1. Access the PostgreSQL Container

Run the following command to enter the PostgreSQL shell:

`docker exec -it n8n-postgres-1 psql -U root -d automations`

2.	Run the SQL Command:
Paste the SQL above into the PostgreSQL shell to create the table.

`CREATE TABLE ai_agent_support_conversations (key TEXT NOT NULL UNIQUE, email TEXT, conversationId TEXT, threadId TEXT, source TEXT, createdAt TIMESTAMP NOT NULL DEFAULT NOW());`

3.	Verify the Table:

	•	List the tables:

`\dt`

•	Check the schema of the conversations table:

`\d ai_agent_support_conversations`

4. Exit the Shell

Type:

`\q`
