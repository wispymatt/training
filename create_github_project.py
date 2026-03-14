#!/usr/bin/env python3
"""
Script to create a new GitHub repository and GitHub Project using the GitHub API.

Usage:
    export GITHUB_TOKEN=<your_personal_access_token>
    python3 create_github_project.py --repo-name my-new-repo --project-name "My New Project"

Requirements:
    - GITHUB_TOKEN environment variable with a PAT that has:
        - repo scope (for creating repos)
        - project scope (for creating GitHub Projects)
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error


GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"


def make_request(url, method="GET", data=None, token=None):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "create-github-project/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"HTTP {e.code}: {error_body}", file=sys.stderr)
        raise


def graphql_request(query, variables, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "create-github-project/1.0",
    }
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(GITHUB_GRAPHQL, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
    if "errors" in result:
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    return result["data"]


def get_authenticated_user(token):
    return make_request(f"{GITHUB_API}/user", token=token)


def create_repository(name, description, private, token):
    data = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": True,
    }
    return make_request(f"{GITHUB_API}/user/repos", method="POST", data=data, token=token)


def create_github_project(owner_id, title, token):
    """Create a GitHub Project (v2) using GraphQL."""
    mutation = """
    mutation CreateProject($ownerId: ID!, $title: String!) {
      createProjectV2(input: {ownerId: $ownerId, title: $title}) {
        projectV2 {
          id
          number
          url
          title
        }
      }
    }
    """
    variables = {"ownerId": owner_id, "title": title}
    result = graphql_request(mutation, variables, token)
    return result["createProjectV2"]["projectV2"]


def link_repo_to_project(project_id, repo_id, token):
    """Link a repository to a GitHub Project."""
    mutation = """
    mutation LinkRepoToProject($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item {
          id
        }
      }
    }
    """
    variables = {"projectId": project_id, "contentId": repo_id}
    return graphql_request(mutation, variables, token)


def main():
    parser = argparse.ArgumentParser(description="Create a new GitHub repo and project")
    parser.add_argument("--repo-name", required=True, help="Name for the new repository")
    parser.add_argument("--repo-description", default="", help="Repository description")
    parser.add_argument("--project-name", required=True, help="Name for the GitHub Project")
    parser.add_argument("--private", action="store_true", help="Make the repository private")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Get authenticated user info
    print("Fetching authenticated user...")
    user = get_authenticated_user(token)
    print(f"Authenticated as: {user['login']} (ID: {user['node_id']})")

    # Create repository
    print(f"\nCreating repository '{args.repo_name}'...")
    repo = create_repository(
        name=args.repo_name,
        description=args.repo_description,
        private=args.private,
        token=token,
    )
    print(f"Repository created: {repo['html_url']}")
    print(f"  - Clone URL: {repo['clone_url']}")
    print(f"  - Default branch: {repo['default_branch']}")

    # Create GitHub Project (v2)
    print(f"\nCreating GitHub Project '{args.project_name}'...")
    project = create_github_project(
        owner_id=user["node_id"],
        title=args.project_name,
        token=token,
    )
    print(f"Project created: {project['url']}")
    print(f"  - Project number: {project['number']}")

    print("\nDone!")
    print(f"\nSummary:")
    print(f"  Repository: {repo['html_url']}")
    print(f"  Project:    {project['url']}")


if __name__ == "__main__":
    main()
