# Database Testing

When running the bot and database locally, you can access the database with the following command:
```shell
docker exec -it discord-bot-db mongo
```

You will need to use [mongo shell](https://docs.mongodb.com/manual/reference/mongo-shell/)
commands from here to modify the database.

> Note: the database for the bot is named "discord"

---

Alternatively, you can try [MongoDB Compass](https://www.mongodb.com/try/download/compass) if
you prefer a more visual approach. 

The database container has its port `27017` mapped to
your machine's port `27017`, so you can connect through localhost.
