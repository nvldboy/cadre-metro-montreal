"""Mise à jour sûre de l'horaire GTFS compact depuis un manifeste Web."""

import json
import os
import socket

try:
    import uhashlib as hashlib
except ImportError:
    import hashlib

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

READ_SIZE = 1024
MAX_MANIFEST_BYTES = 4096
MAX_SCHEDULE_BYTES = 250000
SCHEDULE_FILE = "metro_schedule_data.py"
TEMPORARY_FILE = SCHEDULE_FILE + ".download"
BACKUP_FILE = SCHEDULE_FILE + ".backup"


class GtfsUpdateError(Exception):
    pass


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _remove_if_present(path):
    try:
        os.remove(path)
    except OSError:
        pass


def parse_url(url):
    separator = url.find("://")
    if separator < 0:
        raise GtfsUpdateError("URL de mise à jour invalide")
    scheme = url[:separator].lower()
    if scheme not in ("http", "https"):
        raise GtfsUpdateError("Protocole de mise à jour non accepté")

    remainder = url[separator + 3:]
    slash = remainder.find("/")
    if slash < 0:
        authority = remainder
        path = "/"
    else:
        authority = remainder[:slash]
        path = remainder[slash:]
    if not authority or not path.startswith("/"):
        raise GtfsUpdateError("URL de mise à jour incomplète")

    default_port = 443 if scheme == "https" else 80
    if ":" in authority:
        host, raw_port = authority.rsplit(":", 1)
        try:
            port = int(raw_port)
        except ValueError:
            raise GtfsUpdateError("Port de mise à jour invalide")
    else:
        host = authority
        port = default_port
    if not host or port <= 0 or port > 65535:
        raise GtfsUpdateError("Serveur de mise à jour invalide")
    return scheme, host, port, path


def resolve_relative_url(manifest_url, filename):
    if not isinstance(filename, str) or not filename:
        raise GtfsUpdateError("Nom de fichier GTFS absent")
    if (
        "/" in filename
        or "\\" in filename
        or filename in (".", "..")
    ):
        raise GtfsUpdateError("Nom de fichier GTFS non sécuritaire")
    base = manifest_url.rsplit("/", 1)[0]
    return base + "/" + filename


async def _close_writer(writer):
    writer.close()
    wait_closed = getattr(writer, "wait_closed", None)
    if wait_closed is not None:
        await wait_closed()


async def _open_response(url):
    scheme, host, port, path = parse_url(url)
    connect_host = socket.getaddrinfo(
        host,
        port,
        0,
        socket.SOCK_STREAM,
    )[0][-1][0]
    if scheme == "https":
        reader, writer = await asyncio.open_connection(
            connect_host,
            port,
            ssl=True,
            server_hostname=host,
        )
    else:
        reader, writer = await asyncio.open_connection(connect_host, port)

    default_port = 443 if scheme == "https" else 80
    host_header = host if port == default_port else "{}:{}".format(host, port)
    request = (
        "GET {} HTTP/1.1\r\n"
        "Host: {}\r\n"
        "Accept: application/json, text/plain\r\n"
        "Accept-Encoding: identity\r\n"
        "User-Agent: metro-montreal-led-pico/1.0\r\n"
        "Connection: close\r\n\r\n"
    ).format(path, host_header)
    writer.write(request.encode())
    drain = getattr(writer, "drain", None)
    if drain is not None:
        await drain()

    status_line = await reader.readline()
    parts = status_line.decode().strip().split(" ", 2)
    if len(parts) < 2:
        await _close_writer(writer)
        raise GtfsUpdateError("Réponse HTTP de mise à jour invalide")
    status_code = int(parts[1])
    headers = {}
    while True:
        line = await reader.readline()
        if line in (b"", b"\r\n", b"\n"):
            break
        key, value = line.decode().split(":", 1)
        headers[key.lower().strip()] = value.strip()

    if status_code != 200:
        await _close_writer(writer)
        raise GtfsUpdateError(
            "Réponse HTTP de mise à jour: {}".format(status_code)
        )
    return reader, writer, headers


async def _read_exact_chunks(reader, size, consume):
    remaining = size
    while remaining:
        data = await reader.read(min(READ_SIZE, remaining))
        if not data:
            raise GtfsUpdateError("Téléchargement GTFS tronqué")
        consume(data)
        remaining -= len(data)


async def _read_body(reader, headers, consume):
    total = 0

    def counted_consume(data):
        nonlocal total
        total += len(data)
        consume(data)

    transfer_encoding = headers.get("transfer-encoding", "").lower()
    if transfer_encoding == "chunked":
        while True:
            size_line = await reader.readline()
            if not size_line:
                raise GtfsUpdateError("Réponse HTTP chunked tronquée")
            size = int(size_line.split(b";", 1)[0], 16)
            if size == 0:
                while True:
                    trailer = await reader.readline()
                    if trailer in (b"", b"\r\n", b"\n"):
                        break
                break
            await _read_exact_chunks(reader, size, counted_consume)
            if await reader.readexactly(2) != b"\r\n":
                raise GtfsUpdateError("Séparateur HTTP chunked invalide")
    elif "content-length" in headers:
        await _read_exact_chunks(
            reader,
            int(headers["content-length"]),
            counted_consume,
        )
    else:
        while True:
            data = await reader.read(READ_SIZE)
            if not data:
                break
            counted_consume(data)
    return total


async def _download_manifest(url):
    reader = None
    writer = None
    body = bytearray()
    try:
        reader, writer, headers = await _open_response(url)
        content_length = int(headers.get("content-length", "0") or "0")
        if content_length > MAX_MANIFEST_BYTES:
            raise GtfsUpdateError("Manifeste GTFS trop volumineux")

        def consume(data):
            if len(body) + len(data) > MAX_MANIFEST_BYTES:
                raise GtfsUpdateError("Manifeste GTFS trop volumineux")
            body.extend(data)

        await _read_body(reader, headers, consume)
        return json.loads(body.decode("utf-8"))
    finally:
        if writer is not None:
            await _close_writer(writer)


def _sha256_hex(hasher):
    return "".join("{:02x}".format(byte) for byte in hasher.digest())


async def _download_schedule(url, path, expected_size, expected_sha256):
    reader = None
    writer = None
    hasher = hashlib.sha256()
    total = 0
    _remove_if_present(path)
    try:
        reader, writer, headers = await _open_response(url)
        content_length = int(headers.get("content-length", "0") or "0")
        if content_length and content_length != expected_size:
            raise GtfsUpdateError("Taille HTTP GTFS inattendue")
        if content_length > MAX_SCHEDULE_BYTES:
            raise GtfsUpdateError("Horaire GTFS trop volumineux")

        with open(path, "wb") as handle:
            def consume(data):
                nonlocal total
                total += len(data)
                if total > MAX_SCHEDULE_BYTES:
                    raise GtfsUpdateError("Horaire GTFS trop volumineux")
                handle.write(data)
                hasher.update(data)

            await _read_body(reader, headers, consume)

        if total != expected_size:
            raise GtfsUpdateError(
                "Taille GTFS invalide: {} au lieu de {}".format(
                    total,
                    expected_size,
                )
            )
        actual_sha256 = _sha256_hex(hasher)
        if actual_sha256 != expected_sha256:
            raise GtfsUpdateError("Empreinte SHA-256 GTFS invalide")
        return total
    except Exception:
        _remove_if_present(path)
        raise
    finally:
        if writer is not None:
            await _close_writer(writer)


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise GtfsUpdateError("Version de manifeste GTFS inconnue")
    required_strings = (
        "file",
        "sha256",
        "feed_start",
        "feed_end",
        "feed_version",
        "generated_at",
    )
    for key in required_strings:
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise GtfsUpdateError("Champ de manifeste absent: {}".format(key))
    if (
        len(manifest["feed_start"]) != 8
        or len(manifest["feed_end"]) != 8
        or not manifest["feed_start"].isdigit()
        or not manifest["feed_end"].isdigit()
    ):
        raise GtfsUpdateError("Période GTFS invalide")
    size = manifest.get("size")
    if type(size) is not int or size <= 0 or size > MAX_SCHEDULE_BYTES:
        raise GtfsUpdateError("Taille de manifeste GTFS invalide")
    digest = manifest["sha256"].lower()
    if (
        len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise GtfsUpdateError("Empreinte de manifeste GTFS invalide")
    resolve_relative_url("https://validation.invalid/latest.json", manifest["file"])
    manifest["sha256"] = digest
    return manifest


def update_available(manifest, current_feed, current_generated_at):
    current_end = str(current_feed[1])
    candidate_end = manifest["feed_end"]
    if candidate_end < current_end:
        return False
    if candidate_end > current_end:
        return True
    if manifest["feed_version"] != str(current_feed[2]):
        return manifest["generated_at"] > current_generated_at
    return manifest["generated_at"] > current_generated_at


def _validate_downloaded_schedule(path, manifest):
    with open(path, "r") as handle:
        header = handle.read(1024)
    expected_feed = "FEED = {!r}".format(
        (
            manifest["feed_start"],
            manifest["feed_end"],
            manifest["feed_version"],
        )
    )
    expected_generation = "GENERATED_AT = {!r}".format(
        manifest["generated_at"]
    )
    if (
        "Horaire métro compact" not in header
        or expected_feed not in header
        or expected_generation not in header
    ):
        raise GtfsUpdateError("Métadonnées du fichier GTFS invalides")


def install_schedule(
    temporary=TEMPORARY_FILE,
    target=SCHEDULE_FILE,
    backup=BACKUP_FILE,
):
    if not _exists(temporary):
        raise GtfsUpdateError("Fichier GTFS temporaire absent")
    if not _exists(target):
        raise GtfsUpdateError("Horaire GTFS actuel absent")

    _remove_if_present(backup)
    os.rename(target, backup)
    try:
        os.rename(temporary, target)
    except Exception:
        if not _exists(target) and _exists(backup):
            os.rename(backup, target)
        raise


def recover_schedule(
    target=SCHEDULE_FILE,
    temporary=TEMPORARY_FILE,
    backup=BACKUP_FILE,
):
    restored = False
    if not _exists(target) and _exists(backup):
        os.rename(backup, target)
        restored = True
    if _exists(target):
        _remove_if_present(temporary)
    return restored


def confirm_schedule(backup=BACKUP_FILE):
    _remove_if_present(backup)


def rollback_schedule(
    target=SCHEDULE_FILE,
    temporary=TEMPORARY_FILE,
    backup=BACKUP_FILE,
):
    if not _exists(backup):
        return False
    _remove_if_present(target)
    os.rename(backup, target)
    _remove_if_present(temporary)
    return True


async def check_and_install_update(
    manifest_url,
    current_feed,
    current_generated_at,
    target=SCHEDULE_FILE,
):
    manifest = validate_manifest(await _download_manifest(manifest_url))
    if not update_available(manifest, current_feed, current_generated_at):
        return False

    temporary = target + ".download"
    backup = target + ".backup"
    schedule_url = resolve_relative_url(manifest_url, manifest["file"])
    await _download_schedule(
        schedule_url,
        temporary,
        manifest["size"],
        manifest["sha256"],
    )
    try:
        _validate_downloaded_schedule(temporary, manifest)
        install_schedule(temporary, target, backup)
    except Exception:
        _remove_if_present(temporary)
        raise
    return True
