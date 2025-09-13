import discord
from typing import Dict, Any
import logging
from config import DISCORD_BOT_TOKEN

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordService:
    def __init__(self):
        # Set up Discord client with necessary intents for API operations
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.client = discord.Client(intents=intents)
        self.token = DISCORD_BOT_TOKEN
        
    async def connect(self):
        """Connect to Discord"""
        try:
            if not self.client.is_closed():
                await self.client.close()
            
            # Create a new client instance for fresh connection
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            self.client = discord.Client(intents=intents)
            
            await self.client.login(self.token)
            logger.info("Discord API client logged in successfully")
        except discord.LoginFailure as e:
            logger.error(f"Failed to login to Discord: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Discord"""
        try:
            await self.client.close()
            logger.info("Discord client disconnected")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    async def search_and_delete_messages(
        self, 
        channel_id: int, 
        order_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for messages in a channel and delete those matching the order ID
        
        Args:
            channel_id: Discord channel ID
            order_id: Order ID to match in webhook messages
            limit: Maximum number of messages to search (default: 50)
            
        Returns:
            Dict with operation results
        """
        try:
            # Always create a fresh connection for each request
            await self.connect()
            
            # Fetch the channel from Discord API
            try:
                channel = await self.client.fetch_channel(channel_id)
            except discord.NotFound:
                return {
                    "success": False,
                    "error": f"Channel with ID {channel_id} not found",
                    "deleted_count": 0
                }
            except discord.Forbidden:
                return {
                    "success": False,
                    "error": f"Bot doesn't have permission to access channel {channel_id}",
                    "deleted_count": 0
                }
            
            deleted_messages = []
            messages_checked = 0
            
            # Search through recent messages
            async for message in channel.history(limit=limit):
                messages_checked += 1
                
                # Log message details for debugging
                logger.info(f"Message {messages_checked}: ID={message.id}")
                logger.info(f"  Author: {message.author} (bot: {message.author.bot})")
                logger.info(f"  Webhook ID: {message.webhook_id}")
                logger.info(f"  Content: {message.content}")
                
                # Log embed information
                if message.embeds:
                    for i, embed in enumerate(message.embeds):
                        logger.info(f"  Embed {i+1}:")
                        logger.info(f"    Title: {embed.title}")
                        logger.info(f"    Description: {embed.description}")
                        for j, field in enumerate(embed.fields):
                            logger.info(f"    Field {j+1}: {field.name} = {field.value}")
                
                # Check if this is a webhook message (usually from integrations)
                if message.webhook_id or message.author.bot:
                    logger.info(f"  -> This is a webhook/bot message")
                    
                    # Check message content and embed fields for order ID
                    found_order_id = False
                    
                    # Check content
                    if order_id in message.content:
                        found_order_id = True
                        logger.info(f"  -> Order ID '{order_id}' found in message content!")
                    
                    # Check embeds
                    for embed in message.embeds:
                        if embed.title and order_id in embed.title:
                            found_order_id = True
                            logger.info(f"  -> Order ID '{order_id}' found in embed title!")
                        if embed.description and order_id in embed.description:
                            found_order_id = True
                            logger.info(f"  -> Order ID '{order_id}' found in embed description!")
                        for field in embed.fields:
                            if order_id in field.name or order_id in field.value:
                                found_order_id = True
                                logger.info(f"  -> Order ID '{order_id}' found in embed field: {field.name} = {field.value}")
                    
                    if found_order_id:
                        
                        try:
                            # Delete the message
                            await message.delete()
                            deleted_messages.append({
                                "message_id": message.id,
                                "content": message.content[:100] + "..." if len(message.content) > 100 else message.content,
                                "author": str(message.author),
                                "timestamp": message.created_at.isoformat()
                            })
                            logger.info(f"Deleted message {message.id} from {message.author}")
                            
                        except discord.NotFound:
                            logger.warning(f"Message {message.id} was already deleted")
                        except discord.Forbidden:
                            logger.error(f"No permission to delete message {message.id}")
                        except Exception as e:
                            logger.error(f"Error deleting message {message.id}: {e}")
                    else:
                        logger.info(f"  -> Order ID '{order_id}' NOT found in message content or embeds")
                else:
                    logger.info(f"  -> This is NOT a webhook/bot message, skipping")
            
            return {
                "success": True,
                "deleted_count": len(deleted_messages),
                "messages_checked": messages_checked,
                "deleted_messages": deleted_messages,
                "search_criteria": {
                    "order_id": order_id
                }
            }
            
        except discord.Forbidden:
            return {
                "success": False,
                "error": "Bot doesn't have permission to read messages or delete messages in this channel",
                "deleted_count": 0
            }
        except Exception as e:
            logger.error(f"Error in search_and_delete_messages: {e}")
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0
            }
        finally:
            # Disconnect after operation
            await self.disconnect()

# Global instance
discord_service = DiscordService()
