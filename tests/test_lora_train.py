import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("lora_train", Path(__file__).parents[1] / "scripts" / "lora_train.py")
lora_train = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lora_train)


class GemmaLikeTokenizer:
    """Char-level stand-in with Gemma 4's template behaviour: the generation prompt ends with an empty thinking
    channel, a finished assistant turn is rendered without it."""

    def apply_chat_template(self, msgs, add_generation_prompt=False, tokenize=False):
        text = "<bos>" + "".join(f"<|turn>{'model' if m['role'] == 'assistant' else m['role']}\n{m['content']}<turn|>\n"
                                 for m in msgs)
        if add_generation_prompt:
            text += "<|turn>model\n<|channel>thought\n<channel|>"
        return [ord(c) for c in text] if tokenize else text

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [ord(c) for c in text]}


REC = {"messages": [{"role": "user", "content": "review this"}, {"role": "assistant", "content": '{"findings": []}'}]}


def text(ids):
    return "".join(chr(i) for i in ids)


def test_end_of_turn_is_read_from_the_template():
    assert lora_train.end_of_turn(GemmaLikeTokenizer(), REC) == "<turn|>\n"


def test_sequence_is_generation_prompt_plus_answer_and_only_the_answer_is_trained():
    tok = GemmaLikeTokenizer()
    seq, labels = lora_train.encode(tok, REC, 8192, "<turn|>\n")
    prompt = tok.apply_chat_template(REC["messages"][:1], add_generation_prompt=True, tokenize=True)
    assert text(seq) == text(prompt) + '{"findings": []}<turn|>\n'
    assert labels[: len(prompt)] == [-100] * len(prompt) and text(labels[len(prompt):]) == '{"findings": []}<turn|>\n'
    full = tok.apply_chat_template(REC["messages"], tokenize=True)
    assert full[: len(prompt)] != prompt  # the old prefix assumption that stopped gate attempt 2


def test_too_long_examples_are_dropped():
    assert lora_train.encode(GemmaLikeTokenizer(), REC, 20, "<turn|>\n") is None
