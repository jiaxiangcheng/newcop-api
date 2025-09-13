import discord
from discord import app_commands
import logging
from config import DISCORD_BOT_TOKEN

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordBot:
    def __init__(self):
        # Set up Discord bot with necessary intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self.token = DISCORD_BOT_TOKEN
        self.setup_slash_commands()
        self.setup_events()
        
    def setup_events(self):
        """Set up Discord client events"""
        @self.client.event
        async def on_ready():
            logger.info(f'Discord bot logged in as {self.client.user}')
            try:
                synced = await self.tree.sync()
                logger.info(f'Synced {len(synced)} slash commands')

                # Register bot client with Discord service
                from discord_service import discord_service
                discord_service.set_bot_client(self.client)
                logger.info('Bot client registered with Discord service')

            except Exception as e:
                logger.error(f'Failed to sync slash commands: {e}')
    
    def setup_slash_commands(self):
        """Set up slash commands"""
        @self.tree.command(name='bcn', description='Get Barcelona return link')
        async def bcn_command(interaction: discord.Interaction):
            await interaction.response.send_message(
                'Barcelona return link: https://www.seur.com/devoluciones/pages/devolucionInicio.do?id=6b98e763-d1a2-431d-a876-912cfc8cd00b'
            )
            logger.info(f'BCN command used by {interaction.user}')
        
        @self.tree.command(name='madrid', description='Get Madrid return link')
        async def madrid_command(interaction: discord.Interaction):
            await interaction.response.send_message(
                'Madrid return link: https://www.seur.com/devoluciones/pages/devolucionInicio.do?id=78822075-b327-4dd1-920d-7865acbf4365'
            )
            logger.info(f'Madrid command used by {interaction.user}')
        
    async def start(self):
        """Start the Discord bot"""
        try:
            logger.info("Starting Discord bot...")
            await self.client.start(self.token)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Discord bot"""
        try:
            await self.client.close()
            logger.info("Discord bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

# Global instance
discord_bot = DiscordBot()