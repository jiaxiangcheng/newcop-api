import discord
from typing import Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordService:
    def __init__(self):
        self._bot_client: Optional[discord.Client] = None

    def set_bot_client(self, client: discord.Client):
        """Set the Discord bot client to use for API operations"""
        self._bot_client = client
        logger.info("Discord service configured to use bot client")

    def is_ready(self) -> bool:
        """Check if the Discord bot client is ready"""
        return self._bot_client is not None and self._bot_client.is_ready()
    
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
            # Check if bot client is available and ready
            if not self._bot_client:
                return {
                    "success": False,
                    "error": "Discord bot client not configured",
                    "deleted_count": 0
                }

            if not self._bot_client.is_ready():
                return {
                    "success": False,
                    "error": "Discord bot is not ready yet, please try again",
                    "deleted_count": 0
                }

            # Fetch the channel using the bot client
            try:
                channel = await self._bot_client.fetch_channel(channel_id)
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

# Global instance
discord_service = DiscordService()
