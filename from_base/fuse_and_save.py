from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

MODEL_PATH = "/Users/eligross/models/Qwen3.5-4B-OptiQ-4bit"


model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype="bfloat16")


## Load the PEFT model and merge it with the base model
model = PeftModel.from_pretrained(model, "/Users/eligross/models/checkpoint-800")

merged = model.merge_and_unload()

merged.save_pretrained("/Users/eligross/models/Qwen3.5-4B-merged")
## save new tokenizer
tokenizer = AutoTokenizer.from_pretrained("/Users/eligross/models/checkpoint-800")
tokenizer.save_pretrained("/Users/eligross/models/Qwen3.5-4B-merged")