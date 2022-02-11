# surface-oss

lighter version of Surface

## v1 features/apps

* surface-theme - custom face always looks better
* notifications - everyone needs notifications
* customenv - 12factor with VAULT and FILE support
* dkron - scheduled jobs and async tasks
* dns_ips - manage the scope
* scanners - scan the scope managed in `dns_ips`
* scanner_* - for the scanners that are onboarded

## cleanup pending

* TLA field in dns_ips: change to organisation. how does the outter project (such as our Surface) change or add the link to TLA? monkeypatch the admin model with reference to a OneToOne bridge model? Using swappable (like `auth.User`) won't work as dns_ips itself has references to the model and will always create migrations inside... currently using *fake* inventory app)
* import_export mixin?
* move `slack_display` stuff to a model list setting from slackbot, not per admin model
* `core_utils` what to do about it? currently **duplicated** as it's heavily modified in our version

## Quickstart

*For AWS, check [aws-cdk](dev/aws-cdk/README.md) folder*

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
