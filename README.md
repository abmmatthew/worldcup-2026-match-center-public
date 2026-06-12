# FIFA World Cup 2026 Match Centre

This package includes two Streamlit entry points:

- `app.py` - full/admin version with API Debug and data-source controls.
- `app_light.py` - public light version with no sidebar, no API controls, no demo mode, and no API Debug tab.

For a public Streamlit deployment, use:

```text
Main file path: app_light.py
```

Add the API key in Streamlit Cloud secrets:

```toml
BDL_FIFA_API_KEY = "your_real_key_here"
```

The public app uses BALLDONTLIE when available and falls back to the local CSV schedule without exposing API errors to users.
