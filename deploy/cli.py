import json
import os
import sys
from http import HTTPStatus

import httpx
import typer
from yarl import URL

app = typer.Typer()

BUILTIN_VAR_PREFIXES = {"CI_", "FF_", "GITLAB_", "DOCKER_"}
BUILTIN_VARS = {"PATH", "PWD", "OLDPWD", "HOME", "SHLVL", "HOSTNAME", "CI"}


@app.command("deploy")
def deploy(
    portainer_url: str = typer.Option(
        ..., envvar="PORTAINER_URL", help="Portainer instance URL"
    ),
    portainer_username: str = typer.Option(
        ..., envvar="PORTAINER_USERNAME", help="Portainer username"
    ),
    portainer_password: str = typer.Option(
        ..., envvar="PORTAINER_PASSWORD", help="Portainer password"
    ),
    portainer_endpoint_id: int = typer.Option(
        None,
        envvar="PORTAINER_ENDPOINT_ID",
        help="Default portainer endpoint ID.",
    ),
    stack_name: str = typer.Option(..., envvar="STACK_NAME", help="Name of the stack"),
    stack_file: str = typer.Option(
        "docker-stack.yml", envvar="STACK_FILE", help="Path to the stack file"
    ),
    env_var: list[str] = typer.Option(
        None,
        "--env-var",
        "-e",
        help="A list of environment variables used during stack deployment",
    ),
    use_env: bool = typer.Option(
        False, help="Use current environment variables. Be careful, use prefixes"
    ),
    skip_builtin: bool = typer.Option(True, help="Skip built-in CI variables"),
    prefixes: list[str] = typer.Option(
        None,
        "--prefix",
        "-p",
        help="A list of prefixes that used to export variables from current environment",
    ),
):
    api_url = URL(portainer_url) / "api"

    stack_env = _get_env_variables(env_var)
    stack_env += _get_current_env_variables(use_env, prefixes, skip_builtin)
    headers = _get_auth_token(api_url, portainer_username, portainer_password)
    stack_file_content = _get_stackfile_content(stack_file)
    stack = _get_existing_stack(api_url, headers, stack_name)
    if stack:
        stack_id = stack["Id"]
        endpoint_id = stack["EndpointId"]
    else:
        stack_id = None
        endpoint_id = portainer_endpoint_id

    if not endpoint_id:
        endpoint_id = _get_endpoint_id(api_url, headers)

    if stack_id is None:
        swarm_cluster_id = _get_swarm_cluster_id(api_url, headers, endpoint_id)
        _create_stack(
            api_url,
            headers,
            endpoint_id,
            swarm_cluster_id,
            stack_name,
            stack_file_content,
            stack_env,
        )
    else:
        _update_stack(api_url, headers, stack_id, endpoint_id, stack_file_content, stack_env)


def _get_env_variables(env_var: list[str]) -> list[dict[str, str]]:
    stack_env = []
    if env_var:
        typer.echo("Environment variables for stack file:")
        for pair in env_var:
            name, value = pair.split("=", maxsplit=1)
            stack_env.append({"name": name, "value": value})
    else:
        typer.echo("No environment variables for stackfile.")
    return stack_env


def _get_current_env_variables(
    use_env: bool, prefixes: list[str], skip_builtin: bool
) -> list[dict[str, str]]:
    if not use_env:
        return []
    env_vars = _get_env_vars(skip_builtin)
    if not prefixes:
        return [{"name": name, "value": value} for name, value in env_vars.items()]
    stack_env = []
    for name, value in env_vars.items():
        for prefix in prefixes:
            if name.startswith(prefix):
                stack_env.append({"name": name, "value": value})
    return stack_env


def _get_env_vars(skip_builtin: bool) -> dict[str, str]:
    if not skip_builtin:
        return dict(os.environ)
    variables = {}
    for name, value in os.environ.items():
        if name in BUILTIN_VARS:
            continue
        for prefix in BUILTIN_VAR_PREFIXES:
            if not name.startswith(prefix):
                variables[name] = value
    return variables


def _get_auth_token(api_url: URL, username: str, password: str):
    typer.secho("Getting auth token... ", fg=typer.colors.YELLOW, nl=False)
    resp = httpx.post(
        str(api_url / "auth"),
        json={"username": username, "password": password},
        timeout=None,
    )
    if resp.status_code != HTTPStatus.OK:
        typer.secho(
            f"HTTP {resp.status_code} error while trying to obtain JWT token.",
            fg=typer.colors.RED,
        )
        sys.exit(1)
    headers = {"Authorization": "Bearer " + resp.json()["jwt"]}
    typer.secho("done", fg=typer.colors.BRIGHT_GREEN)
    return headers


def _get_stackfile_content(stackfile: str):
    typer.secho("Checking for stackfile... ", fg=typer.colors.YELLOW, nl=False)
    if os.path.isfile(stackfile):
        with open(stackfile) as f:
            stackfile_content = f.read()
    else:
        typer.secho("can't find stackfile", fg=typer.colors.RED)
        sys.exit(1)
    typer.secho("done", fg=typer.colors.BRIGHT_GREEN)
    return stackfile_content


def _get_existing_stack(api_url: URL, headers: dict[str, str], stackname: str):
    typer.secho("Getting target stack ID... ", fg=typer.colors.YELLOW, nl=False)
    resp = httpx.get(str(api_url / "stacks"), headers=headers, timeout=None)
    if resp.status_code != HTTPStatus.OK:
        typer.secho(
            f"HTTP {resp.status_code} error while trying to get list of Portainer stacks",
            fg=typer.colors.RED,
        )
        sys.exit(1)
    stacks = resp.json()
    for stack in stacks:
        if stack["Name"] == stackname:
            typer.secho("Stack found", fg=typer.colors.BRIGHT_GREEN)
            return stack
    typer.secho("stack not found", fg=typer.colors.BRIGHT_YELLOW)
    return None


def _get_endpoint_id(api_url: URL, headers: dict[str, str]):
    typer.secho("Getting endpoint ID... ", fg=typer.colors.YELLOW, nl=False)
    resp = httpx.get(str(api_url / "endpoints"), headers=headers, timeout=None)
    if resp.status_code != HTTPStatus.OK:
        typer.secho(
            f"HTTP {resp.status_code} error while trying to get list of Portainer endpoints",
            fg=typer.colors.RED,
        )
        sys.exit(1)
    endpoints = resp.json()
    if len(endpoints) != 1:
        typer.secho(
            "Unable to define endpoint. Specify the ID using the portainer_endpoint_id parameter"
        )
        sys.exit(1)
    endpoint_id = endpoints[0]["Id"]
    typer.secho(f"Using endpoint with ID = {endpoint_id}", fg=typer.colors.BRIGHT_GREEN)
    return endpoint_id


def _get_swarm_cluster_id(api_url: URL, headers: dict[str, str], endpoint_id: int):
    typer.secho("Getting Swarm cluster ID... ", fg=typer.colors.YELLOW, nl=False)
    resp = httpx.get(
        str(api_url / "endpoints" / str(endpoint_id) / "docker" / "swarm"),
        headers=headers,
        timeout=None,
    )
    if resp.status_code != HTTPStatus.OK:
        typer.secho(
            f"HTTP {resp.status_code} error while trying to get Swarm cluster ID",
            fg=typer.colors.RED,
        )
        sys.exit(1)
    swarm_cluster_id = resp.json()["ID"]
    typer.secho(
        f"using swarm cluster with ID = {swarm_cluster_id}",
        fg=typer.colors.BRIGHT_GREEN,
    )
    return swarm_cluster_id


def _create_stack(
    api_url: URL,
    headers: dict[str, str],
    endpoint_id: int,
    cluster_id: str,
    stack_name: str,
    stack_file_content: str,
    env_vars: list[dict[str, str]],
):
    typer.secho("Creating a new stack... ", fg=typer.colors.YELLOW, nl=False)
    resp = httpx.post(
        str(api_url / "stacks"),
        headers=headers,
        params={
            "type": 1,
            "method": "string",
            "endpointId": endpoint_id,
        },
        json={
            "env": env_vars,
            "name": stack_name,
            "stackFileContent": stack_file_content,
            "swarmID": cluster_id,
        },
        timeout=None,
    )
    typer.secho("done", fg=typer.colors.BRIGHT_GREEN)
    if resp.status_code != HTTPStatus.OK:
        typer.secho(
            f"Deployment failed:\n{json.dumps(resp.json(), indent=2, ensure_ascii=False)}",
            fg=typer.colors.RED,
        )
        sys.exit(1)


def _update_stack(
    api_url: URL,
    headers: dict[str, str],
    stack_id: int,
    endpoint_id: int,
    stack_file_content: str,
    env_vars: list[dict[str, str]],
):
    typer.secho("Updating an existing stack... ", fg=typer.colors.YELLOW, nl=False)
    resp = httpx.put(
        str(api_url / "stacks" / str(stack_id)),
        headers=headers,
        params={"endpointId": endpoint_id},
        json={
            "env": env_vars,
            "prune": False,
            "stackFileContent": stack_file_content,
        },
        timeout=None,
    )
    typer.secho("done", fg=typer.colors.BRIGHT_GREEN)
    if resp.status_code != HTTPStatus.OK:
        typer.secho(
            f"Deployment failed:\n{json.dumps(resp.json(), indent=2, ensure_ascii=False)}",
            fg=typer.colors.RED,
        )
        sys.exit(1)
