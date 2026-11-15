"""Local multilingual NLI veto for claims; no downloads in the request path.

This is an additional evidence checker, not a replacement for Qwen generation.
Model probabilities are fallible support judgments, never answerability scores.
"""

import argparse
from functools import lru_cache

from . import config

NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
NLI_REVISION = "8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c"
NLI_CACHE = config.PROJECT_ROOT / ".cache" / "models"


def evidence_premise(quote: str, metadata: dict) -> str:
    """Include verified scope and parent headings, not just a detached clause."""
    labels = {"university": "sinh viên đại học", "college": "sinh viên cao đẳng",
              "regular": "hình thức chính quy", "part_time": "hình thức vừa làm vừa học"}
    scope = [labels[value] for key in ("levels", "modes") for value in metadata.get(key, [])]
    headings = [metadata.get(key, "") for key in ("article_title", "clause_title", "item_title")]
    parts = (["Phạm vi áp dụng: " + "; ".join(scope) + "."] if scope else [])
    parts.extend(dict.fromkeys(heading for heading in headings if heading))
    return " ".join([*parts, quote])


class LocalEntailment:
    def __init__(self, threshold=0.7):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.threshold = threshold
        options = dict(revision=NLI_REVISION, cache_dir=str(NLI_CACHE), local_files_only=True)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL, **options)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                NLI_MODEL, dtype=torch.float32, use_safetensors=True, **options).eval()
        except OSError as exc:
            raise FileNotFoundError("Thiếu model kiểm chứng NLI cục bộ. Chạy python -m src.entailment --download một lần.") from exc
        labels = {int(key): value.lower() for key, value in self.model.config.id2label.items()}
        if labels != {0: "entailment", 1: "neutral", 2: "contradiction"}:
            raise ValueError("Nhãn NLI không khớp model/revision đã chốt")
        self.max_length = int(self.model.config.max_position_embeddings)

    def check(self, premise: str, hypothesis: str) -> dict:
        import torch

        inputs = self.tokenizer(premise, hypothesis, return_tensors="pt", truncation=False)
        length = inputs["input_ids"].shape[-1]
        if length > self.max_length:
            return {"supported": False, "reason": f"Chứng cứ NLI có {length} token > {self.max_length}; không cắt âm thầm", "scores": {}}
        with torch.inference_mode():
            probabilities = torch.softmax(self.model(**inputs).logits[0], dim=-1).tolist()
        scores = dict(zip(("entailment", "neutral", "contradiction"), map(float, probabilities)))
        return {"supported": scores["entailment"] >= self.threshold, "scores": scores,
                "reason": "NLI yêu cầu chứng cứ suy ra toàn bộ luận điểm", "tokens": length}


@lru_cache(maxsize=1)
def get_entailment():
    return LocalEntailment()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if not args.download:
        parser.error("Dùng --download để chuẩn bị model; truy vấn chỉ đọc cache cục bộ")
    from huggingface_hub import snapshot_download

    folder = snapshot_download(NLI_MODEL, revision=NLI_REVISION, cache_dir=str(NLI_CACHE),
                               allow_patterns=["config.json", "tokenizer.json", "tokenizer_config.json",
                                               "special_tokens_map.json", "added_tokens.json", "spm.model", "model.safetensors"])
    print(folder)


if __name__ == "__main__":
    main()
