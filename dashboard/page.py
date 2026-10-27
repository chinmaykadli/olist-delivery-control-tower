"""Shared HTML shell for the dashboard pages (index.html and ops.html)."""

OK_BLUE = "#2c7fb0"

NAV = [("index.html", "Findings"), ("ops.html", "Operations: peaks, lanes, queue")]


def render(title: str, intro: str, cards: list[tuple[str, str]], sections: list[tuple[str, str, str]],
           active: str) -> str:
    nav = " | ".join(
        f'<b>{label}</b>' if href == active else f'<a href="{href}">{label}</a>' for href, label in NAV)
    card_html = "".join(
        f'<div class="card"><div class="k">{v}</div><div class="l">{k}</div></div>' for k, v in cards)
    section_html = "".join(
        f'<section><h2>{t}</h2><p class="note">{n}</p>{h}</section>' for h, t, n in sections)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
 body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; margin: 0; color: #1c2833; background: #f7f9fa; }}
 header {{ background: #1c2833; color: #fff; padding: 28px 32px; }}
 header h1 {{ margin: 0 0 6px; font-size: 22px; }}
 header p {{ margin: 0; opacity: .8; font-size: 14px; max-width: 900px; }}
 nav {{ background: #fff; border-bottom: 1px solid #e1e8ed; padding: 10px 32px; font-size: 14px; }}
 main {{ max-width: 1000px; margin: 0 auto; padding: 24px 16px 60px; }}
 .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 18px 0 8px; }}
 .card {{ background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; padding: 12px 14px; }}
 .card .k {{ font-size: 19px; font-weight: 700; }}
 .card .l {{ font-size: 12px; color: #5d6d7e; margin-top: 2px; }}
 section {{ background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; padding: 18px 20px; margin-top: 18px; overflow-x: auto; }}
 h2 {{ font-size: 17px; margin: 0 0 4px; }}
 .note {{ font-size: 13px; color: #5d6d7e; margin: 0 0 8px; }}
 table {{ border-collapse: collapse; font-size: 12px; width: 100%; }}
 th, td {{ border-bottom: 1px solid #e1e8ed; padding: 5px 6px; text-align: left; white-space: nowrap; }}
 th {{ background: #f2f4f4; }}
 footer {{ text-align: center; font-size: 12px; color: #7f8c8d; padding: 20px; }}
 a {{ color: {OK_BLUE}; }}
</style></head>
<body>
<header><h1>{title}</h1><p>{intro}</p></header>
<nav>{nav}</nav>
<main>
  <div class="cards">{card_html}</div>
  {section_html}
</main>
<footer>Built with DuckDB, Python and Plotly. Data:
<a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce">Olist Brazilian E-Commerce (Kaggle)</a>, CC BY-NC-SA 4.0.
Case study, not work performed for Olist or any employer.</footer>
</body></html>"""
