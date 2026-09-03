"""
Communication with the main.js for logging and message sending
"""
import sys
import json

def log(message): 
    print(json.dumps({"type": "print", "content": message}), file=sys.stderr, end="\n", flush=True)

def report(message):
    print(json.dumps({"type": "report", "content": message}), file=sys.stderr, end="\n", flush=True)

def resolve(message):
    print(json.dumps(message), end="\n", flush=True)