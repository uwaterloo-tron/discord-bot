# Getting started

Follow this guide to learn how to set up the project, add changes, test, and merge your changes.

## Prerequisites

- :fontawesome-brands-docker: [Docker](https://docs.docker.com/get-docker/) 
- :snake: [Python 3.9](https://www.python.org/downloads/release/python-396/) 
- :poetry: [Poetry](https://python-poetry.org/docs/)


## Installation

### Step 1
**If you are not in the GitHub organization ([uwaterloo-tron](https://github.com/uwaterloo-tron)):**

- Fork the discord-bot repository to your GitHub account using the "fork" button on the top-right of the
  project repo page. Then clone it using one of the following commands:
  ```shell
  # For HTTPS
  git clone https://github.com/YOUR_GITHUB_USERNAME/discord-bot.git && cd discord-bot
  # For SSH
  git clone git@github.com:YOUR_GITHUB_USERNAME/discord-bot.git && cd discord-bot
  ```
    
**If you are in the GitHub organization:**

- Clone the project repo directly using one of the following commands:
  ```shell
  # For HTTPS
  git clone https://github.com/uwaterloo-tron/discord-bot.git && cd discord-bot
  # For SSH
  git clone git@github.com:uwaterloo-tron/discord-bot.git && cd discord-bot
  ```

> NOTE:
> 
> If you would like to become a member of the organization,
[raise an issue](https://github.com/uwaterloo-tron/discord-bot/issues)
asking for an invitation with your Discord ID (e.g. `@username#1234`),
or send a DM to `@Roton#5439` on Discord including your GitHub username.
> 
> We will also send you an invitation to the organization if you make any contributions.


### Step 2

Create a new branch for development:
```shell
git checkout -b "BRANCH-NAME"
```


### Step 3

Run the following command in the project directory:
```shell
poetry install
```

## Development

Check out the [discord.py docs](https://discordpy.readthedocs.io/en/stable/) for help.
Here are some useful pages:

- [Commands](https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html)
  (functions that activate via `<prefix>command-name`, e.g. `?=help`)
- [Tasks](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html)
  (functions which automatically run every set period of time)
- [Event listeners](https://discordpy.readthedocs.io/en/stable/api.html#event-reference)
  (functions which run on specific Discord events, e.g. when joining a guild)

:bangbang: Please read through the
[code conventions](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/code/)
before you start :bangbang:

If you modify the **docs** or **database** in your changes, read through their respective convention pages as well:

- [Database conventions](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/database/)
- [Documentation conventions](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/documentation/)


## Testing

1. [Set up a Discord bot for testing](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/discord_bot/#creating-the-bot)

2. [Invite your bot to a server where you will test it](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/discord_bot/#inviting-the-bot-to-your-server)

3. Create a file named `.env` in the project directory. Inside the file, add the following lines:
  ```shell
  DISCORD_TOKEN=[paste token here]
  STAGE=[your stage (optional)]
  LOG_LEVEL=[desired log level (optional)]
  ```
  > Note: Don't include the square brackets
  - [Where you can get your token](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/discord_bot/#getting-your-bot-token)
  - [Which stage you should use](https://uwaterloo-tron.github.io/discord-bot/Contributing/Testing/stages/)
  - `LOG_LEVEL` must be one of the following:
    
    `CRITICAL`, `ERROR`, `WARNING` (default), `INFO`, `DEBUG`

4. Start the bot and database with the following command:
    ```shell
    docker-compose up --build -d
    ```
  - If you make any changes, run this command again to update the container
  - If you ever want to wipe the database, run this command:
    ```shell
    docker-compose down -v && docker-compose up --build -d
    ```
    **WARNING:** this cannot be undone
     
5. When you are done, tear down by running the following command:
    ```shell
    docker-compose down
    ```
  - **Recommended:** remove all dangling images (previous versions):
    ```shell
    docker image prune -f
    ```  

## Creating a Pull Request

Here's how you can add your changes to the production server for the bot.

### Steps

1. 
Make sure your changes follow the
  [code conventions](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/code/) and
  [database conventions](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/database/)
  - Update the docs if necessary :point_right:
  [check here for more details](https://uwaterloo-tron.github.io/discord-bot/Contributing/Convention%20Guidelines/documentation/)

2. Commit and push your changes
  - See [this guide][1] on how to write great commit messages

3. Open a pull request (PR) on the main project repo

That's all! Once your PR is approved, your changes will be automatically deployed to the production server.

If you're still confused, check out [this guide][2].


[1]: https://chris.beams.io/posts/git-commit/
[2]:
https://medium.com/@jenweber/your-first-open-source-contribution-a-step-by-step-technical-guide-d3aca55cc5a6
