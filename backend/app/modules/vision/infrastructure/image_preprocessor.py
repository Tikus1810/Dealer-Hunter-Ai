"""Image Preprocessor (Band 08 architecture module): fetches and decodes a
listing image. The only I/O in the Vision AI pipeline — everything
downstream (`ObservationEngine`) is pure computation on the decoded image.
"""

from __future__ import annotations

import io

import httpx
from PIL import Image, UnidentifiedImageError


class ImageFetchError(Exception):
    """Raised when an image can't be fetched or decoded. Caught by the
    application service and turned into an 'unreachable' observation
    rather than aborting the whole analysis (Band 08: one image's failure
    doesn't invalidate the others)."""


class ImagePreprocessor:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_and_decode(self, image_url: str) -> Image.Image:
        try:
            response = await self._client.get(image_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ImageFetchError(f"could not fetch {image_url}: {exc}") from exc

        try:
            image = Image.open(io.BytesIO(response.content))
            image.load()  # forces full decode; raises on truncated/corrupt data
        except UnidentifiedImageError as exc:
            raise ImageFetchError(f"could not decode {image_url}: {exc}") from exc

        return image
