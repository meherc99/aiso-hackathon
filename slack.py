import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize the Slack client with your bot token
from dotenv import load_dotenv
load_dotenv()


client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
print(client)

def fetch_all_messages(channel_id):
    """
    Fetch all messages from a Slack channel
    
    Args:
        channel_id: The ID of the channel to fetch messages from
    
    Returns:
        List of all messages from the channel
    """
    all_messages = []
    
    try:
        # Initial call to conversations.history
        result = client.conversations_history(channel=channel_id)
        all_messages.extend(result["messages"])
        
        # Paginate through all messages if there are more
        while result.get("has_more"):
            result = client.conversations_history(
                channel=channel_id,
                cursor=result["response_metadata"]["next_cursor"]
            )
            all_messages.extend(result["messages"])
        
        print(f"Successfully fetched {len(all_messages)} messages")
        return all_messages
        
    except SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}")
        return []

# Example usage
if __name__ == "__main__":
    channel_id = "C09RKGDKDRT"  # Replace with your channel ID
    messages = fetch_all_messages(channel_id)
    
    # Print first few messages
    for msg in messages[:5]:
        print(f"{msg.get('user', 'Unknown')}: {msg.get('text', '')}")