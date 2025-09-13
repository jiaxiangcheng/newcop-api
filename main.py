from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging
from discord_service import discord_service
from bot import discord_bot
from config import API_HOST, API_PORT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Discord Message Deletion API",
    description="API for deleting Discord messages based on order ID",
    version="1.0.0"
)

class DeleteMessageRequest(BaseModel):
    """Request model for delete-discord-message endpoint"""
    channel_id: int = Field(..., description="Discord channel ID where to search for messages")
    order_id: str = Field(..., description="Order ID to match in webhook messages")
    limit: Optional[int] = Field(100, description="Maximum number of messages to search (default: 100)")

class DeleteMessageResponse(BaseModel):
    """Response model for delete-discord-message endpoint"""
    success: bool
    deleted_count: int
    messages_checked: Optional[int] = None
    deleted_messages: Optional[list] = None
    search_criteria: Optional[dict] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Discord Message Deletion API",
        "version": "1.0.0",
        "endpoints": {
            "POST /delete-discord-message": "Delete Discord messages matching order ID"
        }
    }

@app.post("/delete-discord-message", response_model=DeleteMessageResponse)
async def delete_discord_message(request: DeleteMessageRequest):
    """
    Delete Discord messages that match the specified order ID
    
    This endpoint searches for webhook messages in a Discord channel that contain
    the specified order ID, then deletes matching messages.
    
    Args:
        request: DeleteMessageRequest containing order ID
        
    Returns:
        DeleteMessageResponse with operation results
    """
    try:
        logger.info(f"Processing delete request for channel {request.channel_id}")
        logger.info(f"Search criteria - Order ID: {request.order_id}")
        
        # Call the Discord service to search and delete messages
        result = await discord_service.search_and_delete_messages(
            channel_id=request.channel_id,
            order_id=request.order_id,
            limit=request.limit
        )
        
        if result["success"]:
            logger.info(f"Successfully processed request. Deleted {result['deleted_count']} messages")
        else:
            logger.error(f"Request failed: {result.get('error', 'Unknown error')}")
        
        return DeleteMessageResponse(**result)
        
    except Exception as e:
        logger.error(f"Unexpected error in delete_discord_message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "discord-message-deletion-api"}

async def run_servers():
    """Run both FastAPI server and Discord bot concurrently"""
    import uvicorn
    
    # Create uvicorn server
    config = uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info(f"Starting Discord Message Deletion API on {API_HOST}:{API_PORT}")
    logger.info("Starting Discord bot with slash commands...")
    
    # Run both server and bot concurrently
    await asyncio.gather(
        server.serve(),
        discord_bot.start()
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_servers())
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    except Exception as e:
        logger.error(f"Error running servers: {e}")
        raise
