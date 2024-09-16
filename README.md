![GitHub Workflow Status (with branch)](https://img.shields.io/github/actions/workflow/status/surface-security/surface/release.yml)
![Python](https://img.shields.io/badge/python-%3E%3D3.8%2C%3C=3.11-blue)
![Django](https://img.shields.io/badge/Django-%3E%3D3.2%2C%3C4.0-blue)
![Codecov](https://img.shields.io/codecov/c/github/surface-security/surface)

# Surface

Asset inventory tracking and security scanners.

## Quickstart

### AWS

*For AWS, check [aws-cdk](dev/aws-cdk/README.md) folder*

### docker

```
# Clone this repo
git clone https://github.com/surface-security/surface/

# Create a `local.env` for any custom settings
touch surface/local.env

# Launch the docker stack
docker compose -f dev/docker-compose-in-a-box.yml up

# Run the "quick start" script - choose password for `admin` user
dev/box_setup.sh
```

Open http://localhost:8080 and login as `admin`.

`box_setup.sh` created a `local` Rootbox and added the `example`, `httpx` and `nmap` scanners images (all from [here](https://github.com/surface-security/?q=scanner-)).

_You might need to reload `nginx` and `Surface` so the migrations and the webserver are put in effect._ You can do so with `docker container restart dev-nginx-1 dev-surface-1`. 

Quick check:
* add IPAddress or DNSRecord (and tag it `is_external`), create a `Scanner` using `example` image and choose `Run scanner` from the actions dropdown
* check scan logs

## Documentation

We have in-depth documentation and instructions on this repository's [wiki page](https://github.com/surface-security/surface/wiki).
