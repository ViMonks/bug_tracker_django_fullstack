import logging
import os


logger = logging.getLogger(__name__)


def ensure_secrets_file(path: str, fallback_secret_name: str) -> None:
    if os.path.isfile(path):
        return

    import google.auth  # pylint: disable=import-outside-toplevel
    from google.cloud import secretmanager_v1beta1 as sm  # pylint: disable=import-outside-toplevel
    _, project = google.auth.default()

    logger.debug(f'Downloading secret "{fallback_secret_name}"')

    if project:
        client = sm.SecretManagerServiceClient()
        secret_path = client.secret_version_path(project, fallback_secret_name, 'latest')
        payload = client.access_secret_version(secret_path).payload.data.decode('UTF-8')

        with open(path, "w") as f:
            f.write(payload)
