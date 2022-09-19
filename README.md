# gitlab-portainer-deploy

## Usage

In `.gitlab-ci.yml`:

```yaml
deploy:
  stage: deploy
  image: mirrorrim/gitlab-portainer-deploy
  variables:
    PORTAINER_URL: ""
    PORTAINER_USERNAME: ""
    PORTAINER_PASSWORD: ""
    STACK_NAME: ""
    STACK_FILE: "docker-stack.yml"
  script:
    - deploy -e SOME_STACKFILE_VAR=value -e ANOTHER_STACKFILE_VAR=value
```

## CLI help

```bash
$ deploy --help                                                                                                                                                       *[master] 
Usage: deploy [OPTIONS]

Options:
  --portainer-url TEXT            Portainer instance URL  [env var:
                                  PORTAINER_URL; required]

  --portainer-username TEXT       Portainer username  [env var:
                                  PORTAINER_USERNAME; required]

  --portainer-password TEXT       Portainer password  [env var:
                                  PORTAINER_PASSWORD; required]

  --portainer-endpoint-id INTEGER
                                  Default portainer endpoint ID.  [env var:
                                  PORTAINER_ENDPOINT_ID]

  --stack-name TEXT               Name of the stack  [env var: STACK_NAME;
                                  required]

  --stack-file TEXT               Path to the stack file  [env var:
                                  STACK_FILE; default: docker-stack.yml]

  -e, --env-var TEXT              A list of environment variables used during
                                  stack deployment

  --use-env / --no-use-env        Use current environment variables. Be
                                  careful, use prefixes  [default: False]

  --skip-builtin / --no-skip-builtin
                                  Skip built-in CI variables  [default: True]
  -p, --prefix TEXT               A list of prefixes that used to export
                                  variables from current environment

```
