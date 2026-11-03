"""Build a .pptx from a slide plan. Optionally uses a user-supplied .pptx as the base template."""
import io
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches, Pt


def _layout(prs, i):
    return prs.slide_layouts[i] if i < len(prs.slide_layouts) else prs.slide_layouts[-1]


def _clear(prs):
    ids = prs.slides._sldIdLst
    for s in list(ids):
        prs.part.drop_rel(s.rId)
        ids.remove(s)


def _style_title(slide, color):
    if color and slide.shapes.title is not None:
        p = slide.shapes.title.text_frame.paragraphs[0]
        p.font.bold = True
        p.font.color.rgb = color


def build_pptx(plan, df, r, cfg, template_bytes=None):
    custom = template_bytes is not None
    prs = Presentation(io.BytesIO(template_bytes)) if custom else Presentation()
    if custom:
        _clear(prs)
    else:
        prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
    color = None if custom else RGBColor.from_string(cfg["theme"]["primary"])
    sw, sh = prs.slide_width, prs.slide_height
    box = (Inches(0.5), Inches(1.5), sw - Inches(1), sh - Inches(2.2))

    for s in (x for x in plan if x["on"]):
        if s["type"] == "title":
            sl = prs.slides.add_slide(_layout(prs, 0))
            sl.shapes.title.text = s["title"]
            if len(sl.placeholders) > 1:
                sl.placeholders[1].text = " | ".join(b for b in s["bullets"] if b)
            _style_title(sl, color)

        elif s["type"] == "bullets":
            sl = prs.slides.add_slide(_layout(prs, 1))
            sl.shapes.title.text = s["title"]
            body = next((p for p in sl.placeholders if p.placeholder_format.idx == 1), None)
            if body is None:
                body = sl.shapes.add_textbox(*box)
            lines = [b for b in s["bullets"] if b.strip()] or [" "]
            tf = body.text_frame
            tf.word_wrap = True
            tf.text = lines[0]
            for line in lines[1:]:
                tf.add_paragraph().text = line
            size = Pt(24 if len(lines) <= 4 else 20 if len(lines) <= 6 else 16)
            for p in tf.paragraphs:
                p.font.size = size
            _style_title(sl, color)

        elif s["type"] == "chart":
            sl = prs.slides.add_slide(_layout(prs, 5))
            sl.shapes.title.text = s["title"]
            g = r["groups"].head(cfg.get("max_chart_items", 6))
            cd = CategoryChartData()
            cd.categories = [str(i) for i in g.index]
            cd.add_series(r["metric"], [float(v) for v in g.values])
            ch = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, *box, cd).chart
            ch.has_legend = False
            ch.plots[0].has_data_labels = True
            if color:
                f = ch.plots[0].series[0].format.fill
                f.solid()
                f.fore_color.rgb = color
            _style_title(sl, color)

        elif s["type"] == "table":
            sl = prs.slides.add_slide(_layout(prs, 5))
            sl.shapes.title.text = s["title"]
            d = df.iloc[: cfg.get("table_rows", 8), : cfg.get("table_cols", 6)]
            t = sl.shapes.add_table(len(d) + 1, len(d.columns), *box[:3], Inches(0.4) * (len(d) + 1)).table
            for j, col in enumerate(d.columns):
                t.cell(0, j).text = str(col)
            for i, row in enumerate(d.values):
                for j, v in enumerate(row):
                    t.cell(i + 1, j).text = str(v)[:30]
            _style_title(sl, color)

        elif s["type"] == "options":
            sl = prs.slides.add_slide(_layout(prs, 5))
            sl.shapes.title.text = s["title"]
            opts = s.get("options", [])
            best = s.get("best", -1)
            cols = ["Option", "Est. effect", "Impact", "Cost", "Risk", "Speed", "Score"]
            rows = len(opts) + 1
            t = sl.shapes.add_table(rows, len(cols), *box[:3], Inches(0.4) * rows).table
            for j, col in enumerate(cols):
                cell = t.cell(0, j)
                cell.text = col
                for p in cell.text_frame.paragraphs:
                    p.font.bold = True
            for i, o in enumerate(opts):
                vals = [str(o.get("name", "")), str(o.get("est_effect", "")),
                        str(o.get("impact", "")), str(o.get("cost", "")),
                        str(o.get("risk", "")), str(o.get("speed", "")),
                        f"{o.get('score', 0):.2f}"]
                for j, v in enumerate(vals):
                    cell = t.cell(i + 1, j)
                    cell.text = v
                    if i == best:
                        for p in cell.text_frame.paragraphs:
                            p.font.bold = True
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = RGBColor.from_string("D9EAD3")
            _style_title(sl, color)

        elif s["type"] == "scenarios":
            sl = prs.slides.add_slide(_layout(prs, 5))
            sl.shapes.title.text = s["title"]
            rows = s.get("scenarios", [])
            cols = ["Scenario", "Winner", "Score"]
            t = sl.shapes.add_table(len(rows) + 1, len(cols), *box[:3], Inches(0.4) * (len(rows) + 1)).table
            for j, col in enumerate(cols):
                cell = t.cell(0, j)
                cell.text = col
                for p in cell.text_frame.paragraphs:
                    p.font.bold = True
            for i, row in enumerate(rows):
                vals = [str(row.get("name", "")), str(row.get("winner", "")), f"{row.get('score', 0):.2f}"]
                for j, v in enumerate(vals):
                    t.cell(i + 1, j).text = v
            _style_title(sl, color)

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()
