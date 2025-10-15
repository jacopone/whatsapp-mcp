#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('store/messages.db')
cursor = conn.cursor()

# Get all messages with sender name resolution
cursor.execute('''
SELECT
  messages.sender,
  COALESCE(contacts.name, messages.sender) as sender_name,
  SUBSTR(messages.content, 1, 50) as content_preview,
  chats.name as chat_name
FROM messages
LEFT JOIN contacts ON messages.sender = SUBSTR(contacts.jid, 1, INSTR(contacts.jid, "@") - 1)
LEFT JOIN chats ON messages.chat_jid = chats.jid
ORDER BY messages.timestamp DESC
LIMIT 10
''')

print('Recent messages with sender name resolution:')
print('=' * 100)
for sender, sender_name, content, chat_name in cursor.fetchall():
    status = 'RESOLVED' if sender != sender_name else 'Not resolved'
    print(f'{status} | Chat: {chat_name}')
    print(f'  Sender: {sender} -> Name: {sender_name}')
    print(f'  Message: {content}')
    print('-' * 100)

conn.close()
