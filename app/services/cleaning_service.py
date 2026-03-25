import re

from app.repositories.json_repository import save_json


def normalize_whitespace(text):
    text = str(text or "").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_text(text):
    text = normalize_whitespace(text)
    text = re.sub(r"\s*([，。！？：；])\s*", r"\1", text)
    return text


def normalize_keyword(keyword):
    keyword = normalize_text(keyword).lower()
    keyword = re.sub(r"\s+", " ", keyword)
    return keyword


class FAQCleaningService:
    def __init__(self, faq_path):
        self.faq_path = faq_path

    def clean_item(self, item):
        cleaned = {
            "id": normalize_whitespace(item.get("id", "")),
            "category": normalize_keyword(item.get("category", "")),
            "question": normalize_text(item.get("question", "")),
            "answer": normalize_text(item.get("answer", "")),
            "keywords": [],
        }
        seen_keywords = set()
        for keyword in item.get("keywords", []):
            normalized = normalize_keyword(keyword)
            if not normalized or normalized in seen_keywords:
                continue
            seen_keywords.add(normalized)
            cleaned["keywords"].append(normalized)

        if not cleaned["category"]:
            cleaned["category"] = "general"
        return cleaned

    def clean_items(self, items):
        cleaned_items = []
        dedupe_keys = set()
        changed = False

        for raw_item in items:
            item = self.clean_item(raw_item)
            if not item["id"] or not item["question"] or not item["answer"]:
                changed = True
                continue

            dedupe_key = (item["category"], item["question"].lower(), item["answer"].lower())
            if dedupe_key in dedupe_keys:
                changed = True
                continue
            dedupe_keys.add(dedupe_key)
            cleaned_items.append(item)

            if item != raw_item:
                changed = True

        if changed:
            save_json(self.faq_path, cleaned_items)
        return cleaned_items
