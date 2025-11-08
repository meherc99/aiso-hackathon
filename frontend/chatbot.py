from typing import Any, List, Optional, Tuple

import gradio as gr

from chat_logic import Message, build_bot_reply, messages_to_history
from storage import ConversationStore

store = ConversationStore()


def conversation_list_update(selected_id: Optional[str]):
    conversations = store.list_conversations()
    if not conversations:
        return gr.update(choices=[], value=None)

    conversation_ids = [str(item.get("_id") or item.get("id")) for item in conversations]
    if selected_id not in conversation_ids:
        selected_id = conversation_ids[0]

    choices = [
        (item.get("title") or f"Conversation {index + 1}", str(item.get("_id") or item.get("id")))
        for index, item in enumerate(conversations)
    ]
    return gr.update(choices=choices, value=selected_id)


def handle_user_message(
    message: str,
    history: List[Message],
    conversation_id: Optional[str],
) -> Tuple[List[Message], str, str, Any]:
    history = history or []
    cleaned = message.strip()

    if not conversation_id:
        conversation_id = store.create_conversation()

    if not cleaned:
        sidebar_update = conversation_list_update(conversation_id)
        return history, "", conversation_id, sidebar_update

    store.append_message(conversation_id, "user", cleaned)
    bot_reply = build_bot_reply(cleaned)
    store.append_message(conversation_id, "assistant", bot_reply)
    store.update_title_if_missing(conversation_id, cleaned)

    updated_history = [
        *history,
        {"role": "user", "content": cleaned},
        {"role": "assistant", "content": bot_reply},
    ]
    sidebar_update = conversation_list_update(conversation_id)
    return updated_history, "", conversation_id, sidebar_update


def initialize_interface() -> Tuple[List[Message], str, str, Any]:
    conversations = store.list_conversations()
    if conversations:
        conversation_id = str(conversations[0].get("_id") or conversations[0].get("id"))
    else:
        conversation_id = store.create_conversation()
        conversations = store.list_conversations()

    messages = store.fetch_messages(conversation_id)
    history = messages_to_history(messages)
    sidebar_update = conversation_list_update(conversation_id)
    return history, "", conversation_id, sidebar_update


def start_new_conversation() -> Tuple[List[Message], str, str, Any]:
    conversation_id = store.create_conversation()
    sidebar_update = conversation_list_update(conversation_id)
    return [], "", conversation_id, sidebar_update


def clear_current_conversation(conversation_id: Optional[str]) -> Tuple[List[Message], str, str, Any]:
    if conversation_id:
        store.reset_conversation(conversation_id)
        sidebar_update = conversation_list_update(conversation_id)
        messages = store.fetch_messages(conversation_id)
        history = messages_to_history(messages)
        return history, "", conversation_id, sidebar_update

    new_id = store.create_conversation()
    sidebar_update = conversation_list_update(new_id)
    return [], "", new_id, sidebar_update


def load_conversation(conversation_id: Optional[str]) -> Tuple[List[Message], str, str, Any]:
    if not conversation_id:
        new_id = store.create_conversation()
        sidebar_update = conversation_list_update(new_id)
        return [], "", new_id, sidebar_update

    messages = store.fetch_messages(conversation_id)
    history = messages_to_history(messages)
    sidebar_update = conversation_list_update(conversation_id)
    return history, "", conversation_id, sidebar_update


def build_app() -> gr.Blocks:
    theme = gr.themes.Soft(primary_hue="blue", secondary_hue="slate", radius_size="lg")

    with gr.Blocks(theme=theme) as demo:
        conversation_state = gr.State()

        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=240):
                with gr.Row():
                    gr.Markdown("#### Conversations")
                    new_conversation_btn = gr.Button("New", size="sm")
                conversation_list = gr.Radio(
                    label="",
                    show_label=False,
                    choices=[],
                    value=None,
                    interactive=True,
                )

            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="Chat",
                    height=540,
                    type="messages",
                )
                with gr.Row():
                    message = gr.Textbox(
                        show_label=False,
                        placeholder="Send a message…",
                        autofocus=True,
                        lines=1,
                        max_lines=4,
                    )
                    send = gr.Button("➤", size="sm")

        demo.load(
            initialize_interface,
            inputs=None,
            outputs=[chatbot, message, conversation_state, conversation_list],
        )

        message.submit(
            handle_user_message,
            inputs=[message, chatbot, conversation_state],
            outputs=[chatbot, message, conversation_state, conversation_list],
            queue=False,
        )
        send.click(
            handle_user_message,
            inputs=[message, chatbot, conversation_state],
            outputs=[chatbot, message, conversation_state, conversation_list],
            queue=False,
        )

        new_conversation_btn.click(
            start_new_conversation,
            inputs=None,
            outputs=[chatbot, message, conversation_state, conversation_list],
            queue=False,
        )

        conversation_list.change(
            load_conversation,
            inputs=[conversation_list],
            outputs=[chatbot, message, conversation_state, conversation_list],
            queue=False,
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch()
