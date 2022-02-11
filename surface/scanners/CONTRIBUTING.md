# scanners

This app handles a framework for a flexible setup of different scanners and their integration into Surface.

The general approach is to detach the actual scan from Surface hosts so they easily scale and run from outside our infrastructure and with different IPs and jurisdictions.

The `scanning agent host` that we call `rootbox` only needs to be able to run `docker`.  
This app provides an ansible playbook to will setup a clean centos machine with `dockerd` listening on TCP with TLS. 

Check [flow](flow.md) for a couple of random mermaid diagrams.

## Docker image

A valid `scanner` is any docker image that reads an input file and writes output files to `/output` (inside the docker image).

Easily replicated by:

```bash
docker run -v $(pwd)/input:/whatever \
           -v $(pwd)/output:/output \
           MY_SCANNER_IMAGE /whatever/input.txt
```

As rootboxes are expected to be (mainly) hosted outside our network, the official repository group is in [gitlab.com](https://gitlab.com/security.surf/scanners).  
Currently, it's private and the rootbox provisioning playbook takes care of setting up docker authentication to be able to pull images from there.

In summary:

* Create a repository in the mentioned group
* Build a Dockerfile for your scanner with a entrypoint that:
    * Takes only one `POSITIONAL` argument (feel free to have more optional ones) - this will be the input file
    * Write output files to `/output` (inside the container)
    * Do not place "in progress" files in `/output`, only when they are ready to be fetched
* Re-use `.gitlab-ci.yml` from other scanner (no changes required) to have a proper build/publish pipeline

## Config 

The actual scanner parameters are then setup in Surface `Scanner` model as in http://surf.local/scanners/scanner/

The important fields:

* `Image`: the name of the scanner repository, without the whole group
  `https://gitlab.com/security.surf/scanners/nmap` is `nmap`
* `Tag`: usually default `latest` will be fine, but the default gitlab.com pipelines also builds images from branches, so feel free to use a branch tag for testing or versioning
* `Rootbox`: which rootbox to use
* `Input`: the input generator to use.  
   This will be responsible for creating the input file passed to the docker image.  
   Try to re-use the existing ones if they make sense to your scanner. If they don't, see next section on building one.
* `Parser`: the result parser.
   This is function that will take the files from scanner container `/output` and process them (into Surface).  
   Re-using existing parsers won't make sense most of the times (as new scanners usually serve different purposes), but leaving this field blank will use the `Raw Result` parser, that simply takes the whole raw files and saves them to DB.  
   This is useful to make a quick first run of a scanner image without committing any code to Surface (if the input already exists).

## Custom input generator and parser

If you need a new input generator or a new result parser, please create a new app named `scanner_YOURSCANNER`.

In this app, define the new input generator and/or parser in a module named `scanners.py`, it will be auto-discovered and imported by this app.

Defining a input generator in there is simply writing a generator function and register it as scanner input:

```python
from scanners.parsers._input_registry import register


@register('TYPE_OF_RECORD', 'Hostnames with some criteria')
def list_my_stuff():
    """
    :return: iterator with all Hosts/DNS Records that obey this criteria
    """
    for something in SomeModel.objects.filter(field=criteria):
        yield something.hostname
```

Defining a parser in there should look like:

```python
from scanners.parsers._parser_registry import register as parser_register
from scanners.parsers.base import BaseParser


@parser_register('CHOOSE_A_KEY_NAME_FOR_PARSER', 'My Scanner Parser')
class MyScanner(BaseParser):
    def parse(self, rootbox, scanner, timestamp, filepath):
        # filepath will point to a temporary directory holding copies from scanner /output/ files
        # do whatever you please with them
```

## Testing

* Uncomment/run `dockerd` from the `dev/docker-compose.yaml` stack
* Run `dev/add_test_rootbox_and_scanner.py` (or add rootbox/scanner manually)
* Run `manage.py run_scanner YOUR_SCANNER_NAME` and this should start the scanner in your test dockerd
* Run `manage.py resync_rootbox -r YOUR_ROOTBOX` (if it wasn't running already) and it will retrieve the files and process them (check `ScannerResult` if your scanner does not have a specific `parser`, otherwise check your result tables for them)
