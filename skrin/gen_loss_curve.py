# одноразовый скрипт: SVG-график loss/accuracy из реального лога обучения (без matplotlib)
import re, io, os

raw = open("out/train_log.txt", "rb").read()
log = raw.decode("utf-16") if raw.startswith(b"\xff\xfe") else raw.decode("utf-8", "replace")
eps = re.findall(r"epoch\s+(\d+)/\d+\s+loss=([\d.]+)\s+val_acc=([\d.]+)%", log)
assert eps, "нет эпох в логе"
loss = [(int(e), float(l)) for e, l, _ in eps]
acc = [(int(e), float(a)) for e, _, a in eps]
os.makedirs("skrin", exist_ok=True)

W, H, P = 640, 360, 46
def poly(pts, x0, x1, y0, y1, lo, hi):
    return " ".join(f"{P + (x - x0) * (W - 2*P) / (x1 - x0):.1f},{H - P - (y - lo) * (H - 2*P) / (hi - lo):.1f}" for x, y in pts)

xs = [e for e, _ in loss]
x0, x1 = min(xs), max(xs)
def chart(vals, lo, hi, color, label, fmt, title):
    g = "".join(
        f'<line x1="{P}" y1="{H - P - i*(H-2*P)/4:.1f}" x2="{W-P}" y2="{H - P - i*(H-2*P)/4:.1f}" stroke="#e5e7eb"/>'
        f'<text x="{P-6}" y="{H - P - i*(H-2*P)/4 + 4:.1f}" font-size="11" fill="#6b7280" text-anchor="end">{fmt % (lo + i*(hi-lo)/4)}</text>'
        f'<text x="{P + i*(W-2*P)/4:.1f}" y="{H-20}" font-size="11" fill="#6b7280" text-anchor="middle">{min(xs) + i*(x1-min(xs))//4}</text>'
        for i in range(5))
    last = vals[-1][1]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<rect width="{W}" height="{H}" fill="#ffffff"/>'
            f'<text x="{P}" y="26" font-size="17" font-family="Segoe UI,sans-serif" font-weight="600" fill="#111827">{title}</text>'
            f'<text x="{P}" y="46" font-size="12" fill="#6b7280" font-family="Segoe UI,sans-serif">{label}</text>'
            + g +
            f'<polyline points="{poly(vals, min(xs), x1, lo, hi, lo, hi)}" fill="none" stroke="{color}" stroke-width="2.5"/>'
            + "".join(f'<circle cx="{P + (x-min(xs))*(W-2*P)/(x1-min(xs)):.1f}" cy="{H - P - (y-lo)*(H-2*P)/(hi-lo):.1f}" r="3" fill="{color}"/>' for x, y in vals) +
            f'<text x="{W-P}" y="26" font-size="14" font-family="Segoe UI,sans-serif" font-weight="600" fill="{color}" text-anchor="end">{fmt % last}</text>'
            "</svg>")

io.open("skrin/loss_curve.svg", "w", encoding="utf-8").write(
    chart(loss, min(v for _, v in loss), max(v for _, v in loss), "#2563eb", "cross-entropy loss, bag-of-words softmax, SGD lr=0.5, val_acc=100%", "%.1f", "Обучение intent-классификатора (core/finetune.py)"))
print("ok:", len(loss), "epochs")
