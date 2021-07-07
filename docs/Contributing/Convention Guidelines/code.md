# Code Conventions

## General

- In general, all functionality (commands, tasks, event listeners, etc.) should be added to
  [cogs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html), not the bot itself

- Cogs should not depend on each other if possible

- Try to add [typing](https://docs.python.org/3/library/typing.html) where possible

- Add [logging](https://docs.python.org/3/howto/logging.html) where appropriate 

- Comment your code!
  ([docstrings](https://www.python.org/dev/peps/pep-0257/)
  are a great way to explain how your commands work)
  
- Always format your code with [Black](https://github.com/psf/black) before committing
  - For VSCode, you can set the formatting provider to "black" in your settings. 
    [Check this guide](https://dev.to/adamlombard/how-to-use-the-black-python-code-formatter-in-vscode-3lo0).
  - For PyCharm or IntelliJ, try the [BlackConnect plugin](https://plugins.jetbrains.com/plugin/14321-blackconnect). 


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
