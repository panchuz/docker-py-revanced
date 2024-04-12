"""Utilities."""

import json
import re
import subprocess
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import Any

import requests
from loguru import logger
from requests import Response, Session

from src.downloader.sources import APK_MIRROR_APK_CHECK
from src.downloader.utils import status_code_200
from src.exceptions import ScrapingError

default_build = [
    "youtube",
    "youtube_music",
]
possible_archs = ["armeabi-v7a", "x86", "x86_64", "arm64-v8a"]
request_header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (HTML, like Gecko)"
    " Chrome/96.0.4664.93 Safari/537.36",
    "Authorization": "Basic YXBpLWFwa3VwZGF0ZXI6cm01cmNmcnVVakt5MDRzTXB5TVBKWFc4",
    "Content-Type": "application/json",
}
bs4_parser = "html.parser"
changelog_file = "changelog.md"
request_timeout = 60
session = Session()
session.headers["User-Agent"] = request_header["User-Agent"]
updates_file = "updates.json"
changelogs: dict[str, dict[str, str]] = {}


def update_changelog(name: str, response: dict[str, str]) -> None:
    """The function `update_changelog` updates the changelog file.

    Parameters
    ----------
    name : str
        A string representing the name of the change or update.
    response : Dict[str, str]
        The `response` parameter is a dictionary that contains information about the changes made. The keys
    in the dictionary represent the type of change (e.g., "bug fix", "feature", "documentation"), and
    the values represent the specific changes made for each type.
    """
    app_change_log = format_changelog(name, response)
    changelogs[name] = app_change_log


def format_changelog(name: str, response: dict[str, str]) -> dict[str, str]:
    """The `format_changelog` returns formatted changelog string.

    Parameters
    ----------
    name : str
        The `name` parameter is a string that represents the name of the changelog. It is used to create a
    collapsible section in the formatted changelog.
    response : Dict[str, str]
        The `response` parameter is a dictionary that contains information about a release. It has the
    following keys:

    Returns
    -------
        a formatted changelog as a dict.
    """
    final_name = f"[{name}]({response['html_url']})"
    return {
        "ResourceName": final_name,
        "Version": response["tag_name"],
        "Changelog": response["body"],
        "Published On": response["published_at"],
    }


def write_changelog_to_file() -> None:
    """The function `write_changelog_to_file` writes a given changelog json to a file."""
    markdown_table = """| Resource Name | Version | Changelog | Published On |\n
    "|---------|---------|-----------|--------------|\n"""
    for app_data in changelogs.values():
        name_link = app_data["ResourceName"]
        version = app_data["Version"]
        changelog = app_data["Changelog"]
        published_at = app_data["PublishedOn"]

        # Clean up changelog for markdown
        changelog = changelog.replace("\r\n", "<br>")
        changelog = changelog.replace("\n", "<br>")

        # Add row to the Markdown table string
        markdown_table += f"| {name_link} | {version} | {changelog} | {published_at} |\n"
    with Path(changelog_file).open("w", encoding="utf_8") as file1:
        file1.write(markdown_table)


def get_parent_repo() -> str:
    """The `get_parent_repo()` function returns the URL of the parent repository.

    Returns
    -------
        the URL of the parent repository, which is "https://github.com/nikhilbadyal/docker-py-revanced".
    """
    return "https://github.com/nikhilbadyal/docker-py-revanced"


def handle_request_response(response: Response, url: str) -> None:
    """The function handles the response of a GET request and raises an exception if the response code is not 200.

    Parameters
    ----------
    response : Response
        The parameter `response` is of type `Response`, which is likely referring to a response object from
    an HTTP request. This object typically contains information about the response received from the
    server, such as the status code, headers, and response body.
    url: str
        The url on which request was made
    """
    response_code = response.status_code
    if response_code != status_code_200:
        msg = f"Unable to downloaded assets. Reason - {response.text}"
        raise ScrapingError(msg, url=url)


def slugify(string: str) -> str:
    """The `slugify` function converts a string to a slug format.

    Parameters
    ----------
    string : str
        The `string` parameter is a string that you want to convert to a slug format.

    Returns
    -------
        The function `slugify` returns a modified version of the input string in slug format.
    """
    # Convert to lowercase
    modified_string = string.lower()

    # Remove special characters
    modified_string = re.sub(r"[^\w\s-]", "-", modified_string)

    # Replace spaces with dashes
    modified_string = re.sub(r"\s+", "-", modified_string)

    # Remove consecutive dashes
    modified_string = re.sub(r"-+", "-", modified_string)

    # Remove leading and trailing dashes
    return modified_string.strip("-")


def _check_version(output: str) -> None:
    """Check version."""
    if "Runtime Environment" not in output:
        raise subprocess.CalledProcessError(-1, "java -version")
    if "17" not in output and "20" not in output:
        raise subprocess.CalledProcessError(-1, "java -version")


def check_java() -> None:
    """The function `check_java` checks if Java version 17 or higher is installed.

    Returns
    -------
        The function `check_java` does not return any value.
    """
    try:
        jd = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT).decode("utf-8")
        jd = jd[1:-1]
        _check_version(jd)
        logger.debug("Cool!! Java is available")
    except subprocess.CalledProcessError:
        logger.error("Java>= 17 must be installed")
        sys.exit(-1)


def delete_old_changelog() -> None:
    """The function `delete_old_changelog` deleted old changelog file."""
    Path(changelog_file).unlink(missing_ok=True)


def apkmirror_status_check(package_name: str) -> Any:
    """The `apkmirror_status_check` function checks if an app exists on APKMirror.

    Parameters
    ----------
    package_name : str
        The `package_name` parameter is a string that represents the name of the app package to check on
    APKMirror.

    Returns
    -------
        the response from the APKMirror API as a JSON object.
    """
    body = {"pnames": [package_name]}
    response = requests.post(APK_MIRROR_APK_CHECK, json=body, headers=request_header, timeout=60)
    return response.json()


def contains_any_word(string: str, words: list[str]) -> bool:
    """Checks if a string contains any word."""
    return any(word in string for word in words)


def save_patch_info(app: Any) -> None:
    """Save version info a patching resources used to a file."""
    try:
        with Path(updates_file).open() as file:
            old_version = json.load(file)
    except (JSONDecodeError, FileNotFoundError):
        # Handle the case when the file is empty
        old_version = {}  # or any default value you want to assign

    old_version[app.app_name] = {
        "version": app.app_version,
        "integrations_version": app.resource["integrations"]["version"],
        "patches_version": app.resource["patches"]["version"],
        "cli_version": app.resource["cli"]["version"],
        "patches_json_version": app.resource["patches_json"]["version"],
    }
    Path(updates_file).write_text(json.dumps(old_version, indent=4) + "\n")
