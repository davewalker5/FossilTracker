FROM python:3.13-slim-bullseye

ARG VERSION

COPY fossiltracker-${VERSION}.0 /opt/fossiltracker

WORKDIR /opt/fossiltracker

RUN apt-get update -y
RUN pip install --no-cache-dir /opt/fossiltracker/fossil_tracker-${VERSION}-py3-none-any.whl

ENV FOSSIL_TRACKER_DB=/var/opt/fossiltracker/fossiltracker.db
ENV FOSSIL_TRACKER_IMAGES=/var/opt/fossiltracker/images
ENV FOSSIL_TRACKER_DOCUMENTS=/var/opt/fossiltracker/documents
ENV FOSSIL_TRACKER_EXPORT=/var/opt/fossiltracker/export

ENTRYPOINT [ "streamlit" ]
CMD ["run", "/opt/fossiltracker/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
