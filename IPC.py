import sys
import json

def log(message): 
    msg_json = {"type": "print", "message": message}
    print(json.dumps(msg_json), file=sys.stderr, end="", flush=True)

def report(message):
    msg_json = {"type": "report", "message": message}
    print(json.dumps(msg_json), file=sys.stderr, end="", flush=True)

def resolve(message):
    print(json.dumps(message), flush=True)
    sys.exit(1 if message['success'] == False else 0)