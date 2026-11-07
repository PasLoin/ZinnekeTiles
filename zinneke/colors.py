COLORS = {"white":"#ffffff","black":"#000000","transparent":"rgba(0,0,0,0)"}


def c(v):
    if v is None: return None
    s = str(v).strip().lower()
    return COLORS.get(s, str(v))


def lighten(hex_col, amount=0.5):
    h = hex_col.lstrip("#")
    if len(h) == 3: h = "".join(ch * 2 for ch in h)
    if len(h) != 6: return hex_col
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda v: round(v + (255 - v) * amount)
    return "#{:02x}{:02x}{:02x}".format(mix(r), mix(g), mix(b))
