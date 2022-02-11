# some basic troubleshooting for rootbox scanners

## check that your container is running after launching scanner
- `docker ps` on the rootbox server
- check if your container is listed, the name is in the form of `scanner-env-no-scanner_name-timestamp`, e.g. `scanner-prd-60-jboss-1549895952`

## check logs from the scanner container
- on the rootbox server do `journalctl CONTAINER_NAME=xxx` where name is the one listed with `docker ps`

## check `input` and `output` folders
- `cd /scanners_prd/input/` or `.../output/`. The hierarchy of the folders is `/no_scanner-name/timestamp`, e.g. `/60_jboss/1549895952/`

## check docker container events
- e.g. `sudo docker events --since 2019-02-13T08:17:14 | grep jboss`
```
2019-02-13T09:33:28.724917931Z image pull registry.gitlab.com/security.surf/scanners/registry/jboss:latest (name=registry.gitlab.com/security.surf/scanners/registry/jboss)
2019-02-13T09:33:28.968214297Z container create 8af7625dded766d43584a65302491bcffb144e9df42cd6b91221fb7306804c2b (image=registry.gitlab.com/security.surf/scanners/registry/jboss:latest, name=scanner-prd-60-jboss-1550050391)
2019-02-13T09:33:29.945140692Z container start 8af7625dded766d43584a65302491bcffb144e9df42cd6b91221fb7306804c2b (image=registry.gitlab.com/security.surf/scanners/registry/jboss:latest, name=scanner-prd-60-jboss-1550050391)
2019-02-13T18:03:52.454169587Z container die 8af7625dded766d43584a65302491bcffb144e9df42cd6b91221fb7306804c2b (exitCode=0, image=registry.gitlab.com/security.surf/scanners/registry/jboss:latest, name=scanner-prd-60-jboss-1550050391)
2019-02-13T18:03:53.112873931Z container destroy 8af7625dded766d43584a65302491bcffb144e9df42cd6b91221fb7306804c2b (image=registry.gitlab.com/security.surf/scanners/registry/jboss:latest, name=scanner-prd-60-jboss-1550050391)
```
