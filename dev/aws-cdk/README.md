# Surf on AWS

CDK app/stack to deploy Surface in AWS


```shell
➜  surface-oss ✗ cd dev/aws-cdk
➜  aws-cdk ✗ cdk deploy
SurfStack: deploying...

...

Outputs:
SurfStack.lbDNSRecord = SurfS-LB1A1-1EEEEE1JUG11Z-111111111.eu-west-1.elb.amazonaws.com
```

* Point your CNAME to the value of `lbDNSRecord`
* In case of fresh stack (or at least re-created RDS)
  * Run `./ecs-shell.sh './manage.py migrate'` for (django) migrations in case of new deploy (or update)
  * Run `./ecs-shell.sh './manage.py createsuperuser'` to create an admin user
