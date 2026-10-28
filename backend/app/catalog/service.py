import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import HTTPException

from app.config import get_settings

API = "https://openaccess-api.clevelandart.org/api/artworks/"
CATEGORIES = [
    {"slug": slug, "name": name, "image": "/images/placeholder.svg"}
    for slug, name in [
        ("jewelry", "Joias"),
        ("fine-art", "Belas-artes"),
        ("horology", "Relojoaria"),
        ("ceramics", "Cerâmica"),
        ("furniture", "Mobília"),
        ("coins-manuscripts", "Moedas e manuscritos"),
        ("curiosities", "Curiosidades"),
    ]
]


class CatalogService:
    def search(self, query: str = "") -> list[dict]:
        params = {"limit": 20, "cc0": 1, "has_image": 1}
        if query:
            params["q"] = query
        return self._read(API + "?" + urlencode(params))["data"]

    def item(self, item_id: int) -> dict:
        data = self._read(API + str(item_id) + "/")["data"]
        if isinstance(data, list):
            data = next((item for item in data if item["id"] == item_id), None)
        if not data or data.get("id") != item_id:
            raise HTTPException(404, "Item não encontrado")
        if data.get("share_license_status") != "CC0":
            raise HTTPException(422, "Item não disponível para importação")
        return data

    def _read(self, url: str) -> dict:
        try:
            with urlopen(
                Request(url, headers={"User-Agent": "Yorknew/1.0"}), timeout=15
            ) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Resposta muito grande")
            return json.loads(raw)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            raise HTTPException(
                503,
                "Catálogo externo indisponível. "
                "Os lotes publicados continuam disponíveis.",
            ) from None

    def save_image(self, item: dict) -> str:
        url = item.get("images", {}).get("web", {}).get("url", "")
        if (
            urlparse(url).scheme != "https"
            or urlparse(url).netloc != "openaccess-cdn.clevelandart.org"
        ):
            raise HTTPException(422, "Imagem externa inválida")
        try:
            with urlopen(
                Request(url, headers={"User-Agent": "Yorknew/1.0"}), timeout=20
            ) as response:
                if urlparse(response.url).netloc != "openaccess-cdn.clevelandart.org":
                    raise ValueError("Host inválido")
                data = response.read(5_000_001)
            if len(data) > 5_000_000 or not data.startswith(b"\xff\xd8"):
                raise ValueError("Imagem inválida")
        except (HTTPError, URLError, TimeoutError, ValueError):
            raise HTTPException(
                503, "Não foi possível importar a imagem. O lote não foi publicado."
            ) from None
        root = get_settings().media_dir
        root.mkdir(parents=True, exist_ok=True)
        key = uuid4().hex + ".jpg"
        (root / key).write_bytes(data)
        return key
