"""Minimal inference server: loads the trained model from /data/model and serves /generate."""
import os
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = os.getenv("MODEL_DIR", "/data/model")
torch.set_num_threads(int(os.getenv("THREADS", "2")))

tok = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR).eval()
app = FastAPI()


class Request(BaseModel):
    prompt: str
    max_tokens: int = 128


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate(req: Request):
    inputs = tok(f"### Instruction:\n{req.prompt}\n\n### Response:\n", return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=req.max_tokens, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    return {"completion": tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)}
