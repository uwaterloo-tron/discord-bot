# Stages

For reference when you're developing:

The environment variable `ENV` states what environment the bot is running in. It can be one of the following:

- `dev` (default if none is provided):
  - Enables cheats, dev tools, etc. 
  - Use this while you're working on adding features
    

- `staging`:
  - Used to test how your features will work in prod
  - Should be identical to prod, with very few exceptions
    (e.g. Certain features that can only work in the production environment)
      

- `prod`:
  - Reserved for the production server. Use staging instead.

---

You can add code into the bot to enable dev tools and configurations with this.
The value of `ENV` is stored in a variable named `STAGE` in
[config.py](https://github.com/uwaterloo-tron/discord-bot/blob/master/config.py).

Example:

```python
from discord.ext import commands
import config

class SomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def buy(self, ctx, item):
        # buy an item from the shop
    
        # item is free if in dev stage
        price_of_item = 1000 if config.STAGE != 'dev' else 0
        ...
```
