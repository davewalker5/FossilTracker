# fossiltracker

Fossil Tracker is a simple, SQLite-backed application for managing a personal fossil collection. It provides a practical, local-first system for recording specimens, provenance, taxonomy, measurements, documents, images, and notes.

The application consists of a small set of integrated tools:

1. Enter and edit fossil records via Streamlit
2. Explore and validate the data using Datasette
3. Search and browse the collection
4. Maintain supporting reference data

Full documentation, installation guides and the project Wiki are available from the GitHub repository.

## Getting Started

### Prerequisites

Docker must be installed on the host system.

* Windows
* macOS
* Linux

### Usage

#### Container Parameters

The following docker run parameters are recommended when running the fossiltracker image:

| Parameter | Value                         | Purpose                                                 |
| --------- | ----------------------------- | ------------------------------------------------------- |
| -d        | -                             | Run as a background process                             |
| -v        | /local:/var/opt/fossiltracker | Mount the host folder containing the SQLite database    |
| -p        | 80:8501                       | Expose the container's port 8501 as port 80 on the host |
| --rm      | -                             | Remove the container automatically when it stops        |

For example:

```shell
docker run -d \
  -v /local:/var/opt/fossiltracker \
  -p 80:8501 \
  --rm \
  davewalker5/fossiltracker:latest
```

Replace /local with the directory on the host that contains the Fossil Tracker SQLite database and the _images_ and _documents_ folders that hold uploaded images and documents.

#### Volumes

The mounted host folder should contain the SQLite database used by the application:

```
fossiltracker.db
```

If the database does not already exist, initialise it using the instructions in the GitHub repository before starting the container.

#### Running the Application

Start the container:

```shell
docker run -d \
  -v /local:/var/opt/fossiltracker \
  -p 80:8501 \
  --rm \
  davewalker5/fossiltracker:latest
```

Once running, open:

http://localhost:80

to access the Fossil Tracker web interface.

## Find Us

- [Fossil Tracker on GitHub](https://github.com/davewalker5/FossilTracker)

## Versioning

For the versions available, see the [tags on this repository](https://github.com/davewalker5/FossilTracker/tags).

## Authors

- **Dave Walker** - _Initial work_ -

See also the list of [contributors](https://github.com/davewalker5/FossilTracker/contributors) who
participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/davewalker5/FossilTracker/blob/master/LICENSE) file for details.
