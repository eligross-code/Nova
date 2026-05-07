# pip install httpx trafilatura selectolax
import os, httpx
from trafilatura import bare_extraction
from selectolax.lexbor import LexborHTMLParser

SEARX = os.getenv("SEARX_URL", "http://localhost:8080")

def search(query: str, k: int = 5):
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        r = client.get(f"{SEARX}/search", params={"q": query, "format": "json"})
        r.raise_for_status()
        results = r.json().get("results", [])[:k]

        docs = []
        for item in results:
            url = item["url"]
            try:
                html = client.get(url).text
                data = bare_extraction(html, url=url)
                if data and data.get("text"):
                    docs.append({
                        "title": data.get("title") or item.get("title"),
                        "url": url,
                        "text": data["text"][:4000],
                    })
                else:
                    tree = LexborHTMLParser(html)
                    title = tree.css_first("title")
                    docs.append({
                        "title": title.text() if title else item.get("title"),
                        "url": url,
                        "text": tree.text()[:4000],
                    })
            except Exception:
                continue
        return docs

if __name__ == "__main__":
    docs = search("latest AI chip news", k=5)
    for i, d in enumerate(docs, 1):
        print(f"\n[{i}] {d['title']}\n{d['url']}\n{d['text'][:500]}\n")