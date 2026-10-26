"""
Upload Model Card to Hugging Face Model Repository vineet88/hingbert-toxicity-finetuned
"""

from huggingface_hub import HfApi

api = HfApi()

with open("ml-service/MODEL_CARD.md", "r", encoding="utf-8") as f:
    content = f.read()

frontmatter = """---
language:
- en
- hi
license: mit
library_name: transformers
tags:
- toxicity
- content-moderation
- multilingual
- hindi
- hinglish
- roberta
- code-mixed
pipeline_tag: text-classification
widget:
- text: "bhai tu bilkul bekar insan hai chup kar"
- text: "Thank you for the wonderful update!"
- text: "नमस्ते सर, क्या आप मुझे इस प्रोजेक्ट में मदद कर सकते हैं?"
---

"""

full_readme = frontmatter + content
api.upload_file(
    path_or_fileobj=full_readme.encode("utf-8"),
    path_in_repo="README.md",
    repo_id="vineet88/hingbert-toxicity-finetuned",
    repo_type="model",
    commit_message="docs: add comprehensive model card and interactive widget"
)
print("Model Card uploaded successfully to vineet88/hingbert-toxicity-finetuned!")

