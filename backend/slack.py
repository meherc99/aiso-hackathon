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
    channel_id = "C09S2FM7TND"  # Replace with your channel ID
    messages = fetch_all_messages(channel_id)

    # Send messages to parse_messages which will then send to OpenAI
    if messages:
        try:
            from parse_messages import parse_messages_list
            import openai_wrapper
            
            # Parse the messages
            parsed_messages = parse_messages_list(messages)
            print(f"\nParsed {len(parsed_messages)} messages")
            
            # Send to OpenAI
            if parsed_messages:
                json_responses = openai_wrapper.send_messages_to_openai(parsed_messages)
                print(f"\n=== Final Summary ===")
                print(f"Total JSON responses: {len(json_responses)}")
                for i, json_obj in enumerate(json_responses, 1):
                    print(f"\nMeeting {i}:")
                    for key, value in json_obj.items():
                        print(f"  {key}: {value}")
            else:
                print("No valid messages to send to OpenAI")
        except Exception as e:
            print(f"Error processing messages: {e}")