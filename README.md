# Discord Message Deletion API

This is a Python-based REST API for searching and deleting webhook messages that match specific criteria in Discord channels.

## Features

- 🔍 Search webhook messages in Discord channels
- 🎯 Precise matching based on product name, SKU, and size
- 🗑️ Automatically delete matching messages
- 🚀 High-performance REST interface based on FastAPI
- 📊 Detailed operation result reports
- 💬 Discord bot with slash commands for return links

## Installation Steps

### 1. Clone project and set up virtual environment

```bash
cd /path/to/your/project
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# Or on Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Discord Bot Token

Ensure your Discord bot has the following permissions:

- Read Messages
- Read Message History
- Manage Messages

Bot token is already configured in `config.py`.

## Starting the API Service

```bash
python main.py
```

The API will start at `http://localhost:8000`.

You can also start using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Discord Bot Commands

Once the bot is running, these slash commands are available in Discord:

- `/bcn` - Get Barcelona return link
- `/madrid` - Get Madrid return link

## API Usage Guide

### Delete Discord Message Endpoint

**POST** `/delete-discord-message`

#### Request Parameters

```json
{
    "channel_id": 123456789012345678,
    "product_name": "Nike Air Max",
    "sku": "ABC123",
    "size": "US 9",
    "limit": 100
}
```

#### Parameter Description

- `channel_id` (required): Discord channel ID
- `product_name` (required): Product name to match
- `sku` (required): SKU to match
- `size` (required): Size to match
- `limit` (optional): Maximum number of messages to search, default 100

#### Response Example

```json
{
    "success": true,
    "deleted_count": 3,
    "messages_checked": 100,
    "deleted_messages": [
        {
            "message_id": 987654321098765432,
            "content": "Nike Air Max - SKU: ABC123 - Size: US 9 - In Stock!",
            "author": "WebhookBot#0000",
            "timestamp": "2023-12-01T10:30:00.000Z"
        }
    ],
    "search_criteria": {
        "product_name": "Nike Air Max",
        "sku": "ABC123",
        "size": "US 9"
    }
}
```

### Other Endpoints

- **GET** `/` - API information
- **GET** `/health` - Health check
- **GET** `/docs` - Swagger documentation interface

## Usage Examples

### Using curl

```bash
curl -X POST "http://localhost:8000/delete-discord-message" \
     -H "Content-Type: application/json" \
     -d '{
       "channel_id": 123456789012345678,
       "product_name": "Nike Air Max",
       "sku": "ABC123",
       "size": "US 9",
       "limit": 50
     }'
```

### Using Python requests

```python
import requests

url = "http://localhost:8000/delete-discord-message"
data = {
    "channel_id": 123456789012345678,
    "product_name": "Nike Air Max",
    "sku": "ABC123",
    "size": "US 9",
    "limit": 50
}

response = requests.post(url, json=data)
result = response.json()
print(f"Deleted {result['deleted_count']} messages")
```

## How It Works

1. API receives POST request containing channel ID and matching criteria
2. Discord bot connects to specified channel
3. Search recent messages (default 100)
4. Check if each message is a webhook message
5. Verify message content contains all specified matching criteria (product name, SKU, size)
6. Delete matching messages
7. Return operation results

## Important Notes

- Ensure Discord bot is in the target server and has necessary permissions
- API only deletes webhook messages, not regular user messages
- Matching is case-insensitive
- Deletion operations are irreversible, use with caution
- Channel ID can be obtained by right-clicking Discord channel and selecting "Copy ID" (requires developer mode enabled)

## Error Handling

The API handles the following common errors:

- Invalid channel IDs
- Insufficient permissions
- Network connection issues
- Discord API rate limiting

All errors provide detailed information in the response.

## Development

To view API documentation, after starting the service visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`# newcop-api
