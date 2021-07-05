# Code Conventions

## General

- All functionality (commands, tasks, event listeners, etc.) should be added to
  [cogs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html), not the bot itself.

- Cogs should not depend on each other.
  Removing any single cog should have no effect on the functionality of others.

- Try to add [typing](https://docs.python.org/3/library/typing.html) where possible.

- Comment your code!
  ([docstrings](https://www.python.org/dev/peps/pep-0257/)
  are a great way to explain how your commands work)


## New Cogs

Create a new file in the `cogs` directory named
`<something>_cog.py` with the following template:

```python
from discord.ext import tasks, commands
import config

# Note: config.db is the database. TODO remove this line

# TODO rename SomethingCog

class SomethingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # TODO add stuff here


def setup(bot):
    # adds cog to bot from main.py
    bot.add_cog(SomethingCog(bot))
```
