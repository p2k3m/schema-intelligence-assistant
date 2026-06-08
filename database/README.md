# Local SQLite Database Demo

This directory contains a reproducible local database demo. The database is generated from source and is not committed to git.

```bash
python3 database/build_sample_db.py
python3 database/run_db_analysis.py
```

The generated `sample_customer.db` contains synthetic customer, payment, audit, and applicant tables. `schema_sampler.py` converts SQLite metadata and sample rows into the same JSON column descriptor contract used by the detector.

