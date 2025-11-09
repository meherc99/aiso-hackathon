from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import sys
from dotenv import load_dotenv

load_dotenv()

client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

def fetch_all_messages(channel_id, oldest_timestamp=None):
    """
    Fetch all messages from a Slack channel, optionally filtering by timestamp.
    
    Args:
        channel_id: The Slack channel ID
        oldest_timestamp: Unix timestamp (float or string). Only fetch messages after this time.
                         If None, fetches all messages.
    
    Returns:
        List of message dictionaries, or empty list on error.
    """
    try:
        all_messages = []
        cursor = None
        
        # Prepare API parameters
        params = {
            'channel': channel_id,
            'limit': 100
        }
        
        # Add timestamp filter if provided
        if oldest_timestamp is not None:
            # Convert ISO timestamp to Unix timestamp if needed
            if isinstance(oldest_timestamp, str):
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(oldest_timestamp.replace('Z', '+00:00'))
                    oldest_timestamp = dt.timestamp()
                except Exception as e:
                    print(f"Warning: Could not parse timestamp {oldest_timestamp}: {e}", file=sys.stderr)
                    oldest_timestamp = None
            
            if oldest_timestamp is not None:
                params['oldest'] = str(oldest_timestamp)
                print(f"Fetching messages after timestamp: {oldest_timestamp}")
        
        while True:
            if cursor:
                params['cursor'] = cursor
            
            response = client.conversations_history(**params)
            
            messages = response.get('messages', [])
            all_messages.extend(messages)
            
            # Check if there are more messages
            if not response.get('has_more', False):
                break
            
            cursor = response.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
        
        print(f"Successfully fetched {len(all_messages)} messages from channel {channel_id}")
        return all_messages
        
    except SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return []


def get_user_channels():
    """
    Fetch all channel IDs that the bot/user is a member of.
    
    Returns:
        List[str]: List of channel IDs.
        Returns empty list on error.
    """
    try:
        # Fetch all conversations the bot is a member of
        response = client.conversations_list(
            types="public_channel,private_channel",  # Include both public and private
            exclude_archived=True,  # Don't include archived channels
            limit=1000  # Max limit per request
        )
        
        channels = response.get('channels', [])
        
        # Filter to only channels the bot is a member of and extract IDs
        channel_ids = [
            channel['id']
            for channel in channels
            if channel.get('is_member', False)  # Only channels bot is a member of
        ]
        
        print(f"Found {len(channel_ids)} channel(s) the bot is a member of.")
        return channel_ids
        
    except SlackApiError as e:
        print(f"Error fetching channels: {e.response['error']}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Unexpected error fetching channels: {e}", file=sys.stderr)
        return []


def print_channels():
    """Print all channel IDs."""
    channel_ids = get_user_channels()
    
    if not channel_ids:
        print("No channels found or error occurred.")
        return
    
    print("\n" + "="*70)
    print(f"CHANNEL IDs (Total: {len(channel_ids)})")
    print("="*70)
    
    for i, channel_id in enumerate(channel_ids, 1):
        print(f"{i}. {channel_id}")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list-channels":
        print_channels()
    else:
        channel_id = os.getenv("SLACK_CHANNEL_ID", "C09RKGDKDRT")
        print(f"Fetching messages from Slack channel {channel_id}...")
        messages = fetch_all_messages(channel_id)
        
        if messages:
            print(f"Successfully fetched {len(messages)} messages")
            # Print first few for verification
            for msg in messages[:3]:
                print(msg)
        else:
            print("No messages fetched or error occurred.")
