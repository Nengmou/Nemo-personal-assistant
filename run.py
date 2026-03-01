#!/usr/bin/env python3
"""Entry point for Nemo personal assistant bot."""
from dotenv import load_dotenv

load_dotenv()

from nemo.app import start

if __name__ == "__main__":
    start()
