[![GitHub issues](https://img.shields.io/github/issues/davewalker5/FossilTracker)](https://github.com/davewalker5/FossilTracker/issues)
[![Releases](https://img.shields.io/github/v/release/davewalker5/FossilTracker.svg?include_prereleases)](https://github.com/davewalker5/FossilTracker/releases)
[![License](https://img.shields.io/badge/License-mit-blue.svg)](https://github.com/davewalker5/FossilTracker/blob/main/LICENSE)
[![Language](https://img.shields.io/badge/language-python-blue.svg)](https://www.python.org)
[![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/davewalker5/FossilTracker)](https://github.com/davewalker5/FossilTracker/)


# Fossil Tracker

A personal fossil collection catalogue built with Python, SQLite, Streamlit and Datasette.

## Overview

Fossil Tracker is a lightweight application for recording, managing and exploring a personal fossil collection.

Rather than simply maintaining an inventory, the project aims to create a permanent record for each specimen, capturing not only its identity but also its provenance, geological context, taxonomy, morphology and the observations made during its study.

The application forms part of the wider Field Notes project, where computational modelling, natural history and palaeontology are explored through a combination of software, field observations and written articles.

## Objectives

The project is designed to:

- Maintain a structured catalogue of fossil specimens
- Record provenance and acquisition history
- Store taxonomic and geological information
- Capture photographs, measurements and observations
- Link specimens to related Field Notes projects and articles
- Provide a durable SQLite-backed record that can evolve over time

The emphasis is on careful documentation, transparency and long-term maintainability rather than building a comprehensive museum collections management system.

## Technology

The application is built using:

- Python
- SQLite
- yoyo-migrations
- Streamlit
- Datasette

## Planned Features

### Specimen Catalogue

Maintain a record for every fossil in the collection, including:

- Collection number
- Taxonomic identification
- Geological age
- Locality
- Acquisition details
- Preparation type
- Storage location
- Notes and observations

### Provenance

Record where every specimen originated, including:

- Supplier or collector
- Purchase date
- Purchase price
- Provenance documentation
- Ethical and legal notes

### Images

Support multiple photographs for each specimen, including:

- Overall views
- Close-up detail
- Matrix
- Labels
- Comparative images

### Taxonomy

Maintain structured taxonomic information including:

- Kingdom
- Phylum
- Class
- Order
- Family
- Genus
- Species

along with identification confidence where appropriate.

### Geological Context

Record information such as:

- Era
- Period
- Epoch
- Formation
- Member
- Locality

where known.

### Observations

Each specimen can accumulate observations over time, allowing the collection to function as both a catalogue and a research notebook.

## Database Management

Database schema changes are managed using yoyo-migrations.

Every structural change to the database is represented by a migration, providing:

- Reproducible schema creation
- Version-controlled database evolution
- Reversible migrations
- Straightforward setup for new installations

## Getting Started

1. Create and Activate a virtual environment

Run the setup script to create a Python virtual environment and install the project dependencies.

```bash
./scripts/make-venv.sh
. venv/bin/activate
```

2. Initialise the database

Create the SQLite database and apply all outstanding database migrations.

```bash
venv/bin/fossil-tracker init-db
```

By default, the application stores its database at:

```
data/fossil_tracker.sqlite3
```

To use an alternative location, set the FOSSIL_TRACKER_DB environment variable before running the application.

3. Start the Streamlit application

Launch the web interface for managing your fossil collection.

```bash
streamlit run src/fossil_tracker/app.py
```

Once started, Streamlit will display the local URL where the application is available.

4. Browse the database with Datasette (Optional)

The project also includes a Datasette interface for exploring the SQLite database.

```bash
fossil-tracker datasette --port 8001
```

This provides a convenient, read-oriented view of the underlying data and supports ad hoc searching and querying.

5. Seed the database

Populate an empty database with a small set of example specimens.

```bash
fossil-tracker seed
```

The seed command only inserts records when the specimen register is empty, making it safe to run on a newly created database.

6. Import and export CSV data

Specimen records can be exported for backup or interoperability with other applications:

```bash
fossil-tracker export-csv data/fossil_tracker_export.csv
```

They can also be imported as follows:

```bash
fossil-tracker import-csv data/fossil_tracker_export.csv
```

## Roadmap

Planned development includes:

- Core specimen register
- Image management
- Taxonomic reference tables
- Geological reference tables
- Provenance management
- Datasette exploration interface
- Streamlit editing interface
- Markdown export

## Feedback

To file issues or suggestions, please use the [Issues](https://github.com/davewalker5/FossilTracker/issues) page for this project on GitHub.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
