import os
from collections import defaultdict
from datetime import datetime, timezone

import requests

USERNAME = "WISDOM-OSBORN"
README_PATH = "README.md"

LANGUAGE_START = "<!-- LANGUAGES:START -->"
LANGUAGE_END = "<!-- LANGUAGES:END -->"

PROJECTS_START = "<!-- PROJECTS:START -->"
PROJECTS_END = "<!-- PROJECTS:END -->"

UPDATED_START = "<!-- LAST-UPDATED:START -->"
UPDATED_END = "<!-- LAST-UPDATED:END -->"


def github_get(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def get_public_repositories():
    repositories = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?per_page=100&page={page}&sort=updated"
        )

        data = github_get(url)
        if not data:
            break

        repositories.extend(data)
        page += 1

    return [
        repo
        for repo in repositories
        if not repo["fork"] and repo["name"].lower() != USERNAME.lower()
    ]


def get_repository_languages(repository_name: str):
    url = f"https://api.github.com/repos/{USERNAME}/{repository_name}/languages"
    return github_get(url)


def calculate_language_percentages(repositories):
    totals = defaultdict(int)

    for repo in repositories:
        try:
            languages = get_repository_languages(repo["name"])
            for language, byte_count in languages.items():
                totals[language] += byte_count
        except requests.RequestException:
            continue

    total_bytes = sum(totals.values())
    if total_bytes == 0:
        return []

    percentages = [
        (language, byte_count / total_bytes * 100)
        for language, byte_count in totals.items()
    ]

    return sorted(percentages, key=lambda item: item[1], reverse=True)


def create_language_section(language_percentages):
    if not language_percentages:
        return "_No public language statistics available yet._"

    lines = [
        "| Language | Usage |",
        "|---|---:|",
    ]

    for language, percentage in language_percentages[:10]:
        lines.append(f"| {language} | {percentage:.1f}% |")

    lines.extend(
        [
            "",
            "_Calculated from GitHub language statistics for public repositories._",
        ]
    )

    return "\n".join(lines)


def create_projects_section(repositories):
    if not repositories:
        return "_No public repositories found._"

    lines = []

    for repo in repositories[:6]:
        name = repo["name"]
        url = repo["html_url"]
        description = repo.get("description") or "Project documentation coming soon."

        try:
            languages = get_repository_languages(name)
            language_list = ", ".join(list(languages.keys())[:4]) or "Not detected"
        except requests.RequestException:
            language_list = "Not detected"

        updated_at = datetime.fromisoformat(
            repo["updated_at"].replace("Z", "+00:00")
        ).strftime("%d %b %Y")

        lines.extend(
            [
                f"### [{name}]({url})",
                "",
                description,
                "",
                f"**Languages:** {language_list}  ",
                f"**Updated:** {updated_at}",
                "",
            ]
        )

    return "\n".join(lines)


def replace_section(content, start_marker, end_marker, replacement):
    start_index = content.find(start_marker)
    end_index = content.find(end_marker)

    if start_index == -1 or end_index == -1:
        raise ValueError(f"Missing markers: {start_marker} / {end_marker}")

    before = content[: start_index + len(start_marker)]
    after = content[end_index:]

    return f"{before}\n\n{replacement}\n\n{after}"


def main():
    repositories = get_public_repositories()
    languages = calculate_language_percentages(repositories)

    language_section = create_language_section(languages)
    project_section = create_projects_section(repositories)

    timestamp = datetime.now(timezone.utc).strftime("%d %B %Y at %H:%M UTC")
    updated_section = f"_Last automated update: {timestamp}_"

    with open(README_PATH, "r", encoding="utf-8") as file:
        readme = file.read()

    readme = replace_section(readme, LANGUAGE_START, LANGUAGE_END, language_section)
    readme = replace_section(readme, PROJECTS_START, PROJECTS_END, project_section)
    readme = replace_section(readme, UPDATED_START, UPDATED_END, updated_section)

    with open(README_PATH, "w", encoding="utf-8") as file:
        file.write(readme)

    print("Profile README updated successfully.")


if __name__ == "__main__":
    main()
