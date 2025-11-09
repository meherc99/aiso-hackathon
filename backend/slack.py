from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import sys
from dotenv import load_dotenv

load_dotenv()

client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

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

if __name__ == "__main__":
    """
    Quick manual test harness.
    Ensure SLACK_BOT_TOKEN (and optionally SLACK_CHANNEL_ID) plus OPENAI credentials are set.
    """
    channel_id = os.getenv("SLACK_CHANNEL_ID", "C09S2FM7TND")  # Replace with your channel ID
    print(f"Fetching messages from Slack channel {channel_id}...")
    messages = fetch_all_messages(channel_id)

    if not messages:
        print("No messages fetched; aborting.")
        raise SystemExit(1)

    try:
        from parse_messages import parse_messages_list
        from check_meetings import check_for_meetings
        from openai import OpenAI

        parsed_messages = parse_messages_list(messages)
        print(f"\nParsed {len(parsed_messages)} messages")

        if not parsed_messages:
            print("No valid messages to send to OpenAI")
            raise SystemExit(0)

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY / API_KEY is not set.")

        client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))
        json_responses = check_for_meetings(parsed_messages, client)

        print(f"\n=== Final Summary ===")
        print(f"Total JSON responses: {len(json_responses)}")
        for i, json_obj in enumerate(json_responses, 1):
            print(f"\nMeeting {i}:")
            for key, value in json_obj.items():
                print(f"  {key}: {value}")
    except Exception as exc:
        print(f"Error processing messages: {exc}")
