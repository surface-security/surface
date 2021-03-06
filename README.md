# Surface

Asset inventory tracking and security scanners.

## Setting it up

[TODO - list existing settings / enviornment variables and document them]

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

Quick check:
* add IPAddress or DNSRecord (and tag it `is_external`), create a `Scanner` using `example` image and choose `Run scanner` from the actions dropdown
* check scan logs
