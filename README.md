# SIP Discovery Engine (INDmoney) — dashboard starter
1. `pip install -r requirements.txt`
2. `python make_sample.py`  (writes SYNTHETIC demo data to data/export/)
3. `streamlit run app/streamlit_app.py`
Replace data/export/tagged.csv (same columns) with real pipeline output. Never commit .env or raw data.
