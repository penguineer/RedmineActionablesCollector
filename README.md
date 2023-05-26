# Redmine Actionables

![PyTest](https://github.com/penguineer/RedmineActionablesCollector/actions/workflows/pytest.yml/badge.svg)
![Docker Image](https://github.com/penguineer/RedmineActionablesCollector/actions/workflows/docker-image.yml/badge.svg)

> Collect issues from Redmine that can be acted upon

An item is actionable when its action can be executed without further
prerequesites. A Redmine ticket is classified as actionable, when the
following apply:
* it is assigned to >>me<<
* it has started (past start date)
* it is not preceeded by other items
* has no open children
* its parent project is not closed

An actionable item can still be blocked, i.e. it may have open actions, but cannot be completed.

## Usage

### Configuration

Configuration is done using environment variables:

* `PORT`: Target port when used with docker-compose (default `8080`)

### Run with Docker

```bash
docker run --rm -it \
    -p 8080:8080 \
    mrtux/redmine-actionables-collector
```

### Run with Docker-Compose (Development)

To run with [docker-compose](https://docs.docker.com/compose/) copy  [`.env.template`](.env.template) to `.env` and edit the necessary variables. Then start with:

```bash
docker-compose up --build
```

Please note that this compose file will rebuild the image based on the repository. This is helpful during development and not intended for production use.

When done, please don't forget to remove the deployment with
```bash
docker-compose down
```

## Maintainers

* Stefan Haun ([@penguineer](https://github.com/penguineer))

## Contributing

PRs are welcome!

If possible, please stick to the following guidelines:

* Keep PRs reasonably small and their scope limited to a feature or module within the code.
* If a large change is planned, it is best to open a feature request issue first, then link subsequent PRs to this issue, so that the PRs move the code towards the intended feature.


## License

[MIT](LICENSE.txt) © 2020-2023 Stefan Haun and contributors
