#!/usr/bin/env bash
python -m uvicorn web_app:app --host 0.0.0.0 --port 10000
