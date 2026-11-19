#!/bin/bash
cd "$(dirname "$0")"
STREAMLIT_BIN=$(find env -name "streamlit" -type f | head -n 1)
"$STREAMLIT_BIN" run app.py
