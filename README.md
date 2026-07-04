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

Current features include:

- Structured specimen catalogue
- Scientific taxonomy with identification confidence
- Geological ages and localities
- Provenance and acquisition records
- Ethical confidence tracking
- Standardised specimen measurements
- Image and document management
- Observation notes
- Related web links
- Editable reference data
- Full-text specimen search
- SQLite backend with Datasette integration
- Database schema management using yoyo-migrations


## Design Philosophy

Fossil Tracker is built around a few simple principles.

- **Record what you know.** A specimen can be added before every detail is known
- **Preserve evidence.** Images, documents and observations are just as important as structured data
- **Use consistent terminology.** Controlled reference data keeps the collection searchable and maintainable
- **Allow knowledge to evolve.** Taxonomic identifications, provenance and observations can all be refined over time

The aim is not to reproduce a full museum collections management system, but to provide a lightweight, well-structured catalogue for personal collections.

## Technology

The application is built using:

- Python
- SQLite
- yoyo-migrations
- Streamlit
- Datasette

## Getting Started

Further documentation, including the documentation on intended field usage and how to run the application, is available in the project [Wiki](https://github.com/davewalker5/FossilTracker/wiki).

## Feedback

To file issues or suggestions, please use the [Issues](https://github.com/davewalker5/FossilTracker/issues) page for this project on GitHub.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
