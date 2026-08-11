from __future__ import annotations

from app.whatsapp import _green_chat_id, normalize_green_notification


class FakeClient:
    pass


def test_green_chat_id_conversion() -> None:
    assert _green_chat_id("93700123456") == "93700123456@c.us"
    assert _green_chat_id("93700123456@s.whatsapp.net") == "93700123456@c.us"
    assert _green_chat_id("120363000000000@g.us") == "120363000000000@g.us"


def test_normalize_incoming_text_notification() -> None:
    payload = {
        "receiptId": 123,
        "body": {
            "typeWebhook": "incomingMessageReceived",
            "idMessage": "ABC",
            "senderData": {
                "chatId": "93700123456@c.us",
                "sender": "93700123456@c.us",
            },
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {"textMessage": ".ping"},
            },
        },
    }
    message = normalize_green_notification(payload, FakeClient())
    assert message is not None
    assert message.text == ".ping"
    assert message.chat == "93700123456@c.us"
    assert not message.is_group


def test_ignore_non_message_notification() -> None:
    assert normalize_green_notification({"body": {"typeWebhook": "stateInstanceChanged"}}, FakeClient()) is None
