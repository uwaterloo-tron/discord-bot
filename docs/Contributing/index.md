# Getting started

Check out the
[discord.py docs](https://discordpy.readthedocs.io/en/stable/).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Python 3.9](https://www.python.org/downloads/release/python-396/) :snake:
- [pipenv](https://pypi.org/project/pipenv/)


## Installation

Run `pipenv install --dev` in the project directory.


## Testing

1. [Set up a Discord bot for testing](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/discord_bot/#creating-the-bot)

2. [Invite your bot to a server where you will test it](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/discord_bot/#inviting-the-bot-to-your-server)

3. Create a file named `.env` in the project directory. Inside the file, add the following lines:
  ```shell
  DISCORD_TOKEN=[paste token here]
  ENV=[your stage (optional)]
  LOG_LEVEL=[desired log level (optional)]
  ```
  - [Where you can get your token](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/discord_bot/#getting-your-bot-token)
  - [Which stage you should use](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/stages/)
  - `LOG_LEVEL` must be one of the following:
    
    `CRITICAL`, `ERROR`, `WARNING` (default), `INFO`, `DEBUG`

4. Start the bot and database with `docker-compose up --build -d`
  - If you make any changes, run this command again to update the container
  - To reset the database: `docker-compose down -v && docker-compose up --build -d`
    
    **WARNING:** this cannot be undone
     
5. When you are done, tear down by running `docker-compose down`
  - **Recommended:** run `docker image prune -f` to remove all dangling images (previous versions)

## Creating a Pull Request

Here's how you can add your changes to the production server for the bot.

### Steps

1. Fork the discord-bot repository to your GitHub account
- This can be done using the "Fork" button on the top-right of the repository page

2. Clone the fork you created to your machine

3. Create a new branch using `git checkout -b branch-name`

4. Make your additions/changes
- Make sure your changes follow the
  [code conventions](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/code/) and
  [database conventions](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/database/)
- Update the docs if necessary :point_right:
  [check here for more details](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/documentation/)

5. Commit and push your changes
- See [this guide][1] on how to write great commit messages

6. Open a pull request (PR) on the main project repo

That's all! Once your PR is approved, your changes will be automatically deployed to the production server.

If you're still confused, check out [this guide][2].

---

**NOTE:**

Step 1 and 2 only apply to users who are not in the [uwaterloo-tron org][3].
If you are a member of the org, you can clone the repo directly.

If you would like to become a member of the organization,
[raise an issue][4] asking for an invitation with your Discord ID (e.g. `@username#1234`),
or send a DM to `@Roton#5439` on Discord including your GitHub username.

We will also send you an invitation to the organization if you make any contributions.

[1]: https://chris.beams.io/posts/git-commit/
[2]:
https://medium.com/@jenweber/your-first-open-source-contribution-a-step-by-step-technical-guide-d3aca55cc5a6
[3]: https://github.com/uwaterloo-tron
[4]: https://github.com/uwaterloo-tron/discord-bot/issues
