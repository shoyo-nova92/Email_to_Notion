from typing import Any, List

import os

from transformers import pipeline


_DEFAULT_MODEL = "sshleifer/distilbart-cnn-12-6"


class Summarizer:
    def __init__(self, device: str = 'cpu', model_name: str = _DEFAULT_MODEL):
        device_arg = -1
        if device.lower() == 'cuda':
            try:
                import torch  # noqa
                import torch.cuda as cuda  # noqa
                if cuda.is_available():
                    device_arg = 0
            except Exception:
                device_arg = -1
        self.pipe = pipeline("summarization", model=model_name, device=device_arg)

    def chunk_text(self, text: str, max_chars: int = 3000) -> List[str]:
        if not text:
            return [""]
        text = text.strip()
        if len(text) <= max_chars:
            return [text]
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            # try to break on sentence boundary
            window = text[start:end]
            last_period = window.rfind('.')
            if last_period != -1 and (start + last_period + 1) < end:
                end = start + last_period + 1
            chunks.append(text[start:end].strip())
            start = end
        return [c for c in chunks if c]

    def summarize(self, text: str, max_length: int = 120) -> str:
        if not text:
            return ""
        chunks = self.chunk_text(text)
        summaries: List[str] = []
        for chunk in chunks:
            try:
                out = self.pipe(chunk, max_length=max_length, min_length=min(40, max_length // 2), do_sample=False)
                summaries.append(out[0]['summary_text'].strip())
            except Exception as e:
                summaries.append(chunk[:max_length])
        combined = "\n".join(summaries)
        if len(chunks) > 1 and len(combined) > 2000:
            # Summarize the combined summary once more if still long
            try:
                out = self.pipe(combined, max_length=max_length, min_length=min(40, max_length // 2), do_sample=False)
                return out[0]['summary_text'].strip()
            except Exception:
                return combined[:max_length]
        return combined


def init_summarizer(device: str = None) -> Summarizer:
    if device is None:
        device = os.getenv('DEVICE', 'cpu')
    return Summarizer(device=device)



