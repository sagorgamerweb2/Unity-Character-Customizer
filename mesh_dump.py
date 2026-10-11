"""UABE টেক্সট ডাম্প (.txt) → Python dict (typetree) কনভার্টার।
সতর্কতা: এটি best-effort। সবচেয়ে নিরাপদ ফরম্যাট হলো Raw (.dat)।
"""
import re

_ARR = re.compile(r"^\d+\s+Array\s+Array\s+\(\d+\s+items?\)")
_IDX = re.compile(r"^\[(\d+)\]$")
_HEAD = re.compile(r"^\s*\d+\s+(?:Mesh|MonoBehaviour)\s+Base\b", re.M)


class _Node:
    def __init__(self, indent):
        self.indent = indent
        self.type = ""
        self.name = ""
        self.value = None
        self.idx = None
        self.kids = []


def looks_like_text_dump(blob: bytes) -> bool:
    head = blob[:4000]
    if b"\x00" in head:
        return False
    return bool(_HEAD.search(head.decode("utf-8-sig", errors="ignore")))


def _parse_tree(text):
    root = _Node(-1)
    stack = [root]
    for raw in text.splitlines():
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" \t"))
        s = raw.strip()
        n = _Node(indent)
        m = _IDX.match(s)
        if m:
            n.idx = int(m.group(1))
            n.name = f"[{n.idx}]"
        elif _ARR.match(s):
            n.type, n.name = "Array", "Array"
        else:
            left, sep, val = s.partition(" = ")
            toks = left.split()
            if toks and toks[0].isdigit():
                toks = toks[1:]
            if len(toks) >= 2:
                n.name, n.type = toks[-1], " ".join(toks[:-1])
            elif toks:
                n.name = toks[0]
            if sep:
                n.value = val
        while stack and stack[-1].indent >= indent:
            stack.pop()
        stack[-1].kids.append(n)
        stack.append(n)
    return root


def _val(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def _arr_items(arr):
    out = []
    for it in arr.kids:
        if it.idx is not None and it.kids:
            out.append(_conv(it.kids[0]))
    return out


def _conv(n):
    arr = next((k for k in n.kids if k.type == "Array" and k.name == "Array"), None)
    if n.type == "TypelessData":
        size = next((k for k in n.kids if k.name == "size"), None)
        data = next((k for k in n.kids if k.name == "data"), None)
        if data is not None and data.value is not None:
            hx = re.sub(r"[^0-9a-fA-F]", "", data.value)
            out = bytes.fromhex(hx)
        elif arr is not None:
            out = bytes(_arr_items(arr))
        else:
            out = b""
        if size is not None and size.value is not None and int(_val(size.value)) != len(out):
            raise ValueError(f"TypelessData '{n.name}' এর সাইজ মিলছে না")
        return out
    if arr is not None:
        return _arr_items(arr)
    if n.value is not None and not n.kids:
        return _val(n.value)
    return {k.name: _conv(k) for k in n.kids if k.idx is None}


def parse_uabe_dump(text: str) -> dict:
    root = _parse_tree(text)
    if not root.kids:
        raise ValueError("ডাম্প ফাঁকা")
    tree = _conv(root.kids[0])
    if not isinstance(tree, dict) or not tree:
        raise ValueError("ডাম্প থেকে কোনো ফিল্ড পড়া যায়নি")
    return tree


def deep_merge(base, new):
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base
