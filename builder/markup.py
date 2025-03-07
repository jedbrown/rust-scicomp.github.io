import shlex
import re
from datetime import datetime
from citations import markup_citation

page_references = []
ref_map = {}


def markup(content, icons=True, paragraphs=True):
    global page_references

    if "{% no markup %}" in content:
        before, after = content.split("{% no markup %}", 1)
        middle, after = after.split("{% end no markup %}", 1)
        return markup(before, icons) + middle + markup(after, icons)

    while "{{if " in content:
        pre, rest = content.split("{{if ", 1)
        condition, rest = rest.split("}}", 1)
        optional, post = rest.split("{{fi}}", 1)
        condition, options = condition.split(" ", 1)
        content = pre
        if condition in ["before", "after"]:
            options = [int(i) for i in options.split(",")]
            if condition == "before" and datetime.now() < datetime(*options):
                content += optional
            if condition == "after" and datetime.now() > datetime(*options):
                content += optional
        elif condition == "dateis":
            y, m, d = [int(i) for i in options.split(",")]
            y2 = datetime.now().year
            m2 = datetime.now().month
            d2 = datetime.now().day
            if y == y2 and m == m2 and d == d2:
                content += optional
        else:
            raise ValueError(f"Unknown condition: {condition}")
        content += post

    while "<person>" in content:
        a, b = content.split("<person>", 1)
        b, c = b.split("</person>", 1)
        content = a + markup_person(b) + c

    if paragraphs:
        out = ""
        popen = False
        ulopen = False
        code = False
        is_python = False
        for line in content.split("\n"):
            if line.startswith("#"):
                if popen:
                    out += "</p>\n"
                    popen = False
                if ulopen:
                    out += "</ul>\n"
                    ulopen = False
                i = 0
                while line.startswith("#"):
                    line = line[1:]
                    i += 1
                out += f"<h{i}>{line.strip()}</h{i}>\n"
            elif line == "":
                if popen:
                    out += "</p>\n"
                    popen = False
            elif line == "```":
                code = not code
                is_python = False
            elif line == "```python":
                code = not code
                is_python = True
            elif line.startswith("-") or line.startswith("*"):
                if popen:
                    out += "</p>\n"
                    popen = False
                if not ulopen:
                    out += "<ul>\n"
                    ulopen = True
                out += f"<li>{line[1:].strip()}</li>\n"
            else:
                if ulopen:
                    out += "</ul>\n"
                    ulopen = False
                if not popen and not line.startswith("<") and not line.startswith("\\["):
                    if code:
                        out += "<p class='pcode'>"
                    else:
                        out += "<p>"
                    popen = True
                if code:
                    if is_python:
                        out += python_highlight(line.replace(" ", "&nbsp;"))
                    else:
                        out += line.replace(" ", "&nbsp;")
                    out += "<br />"
                else:
                    out += line
                    out += " "
        if popen:
            out += "</p>\n"
            popen = False
        if ulopen:
            out += "</ul>\n"
            ulopen = False
    else:
        out = content

    page_references = []

    out = re.sub(r"<time ([0-2][0-9]):([0-6][0-9])>", r"<span class='bst-time' data-format='{24 0HOUR}:{MINUTE}' data-day='13' data-month='7' data-year='2023' data-hour='\1' data-minute='\2'>\1:\2</span>", out)
    out = re.sub(r"<time Thursday ([0-2][0-9]):([0-6][0-9])>", r"<span class='bst-time' data-format='{24 0HOUR}:{MINUTE}' data-day='13' data-month='7' data-year='2023' data-hour='\1' data-minute='\2'>\1:\2</span>", out)
    out = re.sub(r"<time Friday ([0-2][0-9]):([0-6][0-9])>", r"<span class='bst-time' data-format='{24 0HOUR}:{MINUTE}' data-day='14' data-month='7' data-year='2023' data-hour='\1' data-minute='\2'>\1:\2</span>", out)
    out = re.sub(r"<tzone>", r"<span class='tzone'> BST</span>", out)
    out = out.replace("<timeselector>", "<select id='tzselect' onchange='change_timezone_dropdown(this.value)'></select>")
    out = re.sub(r"<ref ([^>]+)>", add_citation, out)
    out = re.sub(r"<ghostref ([^>]+)>", add_ghost_citation, out)
    out = insert_links(out)
    if icons:
        out = insert_icons(out)

    out = re.sub(r"{{icon:([^}]+)}}", enter_icon, out)
    out = re.sub(r"`([^`]+)`", r"<span style='font-family:monospace'>\1</span>", out)

    if len(page_references) > 0:
        out += "<h2>References</h2>"
        out += "<ul class='citations'>"
        out += "".join([f"<li><a class='refid' id='ref{i+1}'>[{i+1}]</a> {j}</li>"
                        for i, j in enumerate(page_references)])
        out += "</ul>"

    out = insert_dates(out)
    return out


iconlist = []

defelementlist = [
    ("Mardal&ndash;Tai&ndash;Winther", "mardal-tai-winther"),
    ("Arnold&ndash;Winther", "arnold-winther"),
    ("seredipity", "serendipity"),
    ("Lagrange", "lagrange"),
    ("N&eacute;d&eacute;lec", "nedelec1"),
    ("Raviart&ndash;Thomas", "raviart-thomas"),
    ("Scott&ndash;Vogelius", "scott-vogelius"),
    ("Bernstein&ndash;B&eacute;zier", "bernstein"),
]


def enter_icon(matches):
    for t, icon, url in iconlist:
        if matches[1] == t:
            if icon is None:
                return f"<a href='{url}' class='icon'>{t}</a>"
            else:
                return f"<a href='{url}' class='icon'><img src='/img/{icon}'>{t}</a>"
    raise ValueError(f"Icon not found: {matches[1]}")


def insert_icons(txt):
    for t, icon, url in iconlist:
        if icon is None:
            txt = re.sub(
                r"(^|[>\s.!?\(\/])" + t + r"([\s.!?\)\/,']|(?:-based))",
                r"\1<a href='" + url + "' class='icon'>" + t + r"</a>\2",
                txt, 1)
        else:
            txt = re.sub(
                r"(^|[>\s.!?\(\/])" + t + r"([\s.!?\)\/,']|(?:-based))",
                r"\1<a href='" + url + "' class='icon'><img src='/img/" + icon + "'>"
                + t + r"</a>\2",
                txt, 1)
    for e, url in defelementlist:
        txt = txt.replace(e, f"<a class='icon' href='https://defelement.com/elements/{url}.html'>"
                          f"<img src='/img/defelement.png'>{e}</a>", 1)
    # txt = txt.replace("Gather Town", "<a href='/gather-town.html'>Gather Town</a>", 1)
    return txt


def insert_links(txt):
    txt = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)\{([^\}]+)\}",
                 r"<a class='icon' href='\2'><img src='/img/\3'>\1</a>", txt)
    txt = re.sub(r"\[([^\]]+)\]\(([^\)]+)\.md\)", r"<a href='\2.html'>\1</a>", txt)
    txt = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"<a href='\2'>\1</a>", txt)
    txt = re.sub(r"([^'])(https?:\/\/)([^\s\)]+)", r"\1<a href='\2\3'>\3</a>", txt)
    return txt


def add_ghost_citation(matches):
    add_citation(matches)
    return ""


def add_citation(matches):
    global page_references
    global ref_map
    if matches[1] not in ref_map:
        ref = {}
        for i in shlex.split(matches[1]):
            a, b = i.split("=")
            ref[a] = b
        page_references.append(markup_citation(ref))
        ref_map[matches[1]] = len(page_references)
    return f"<a href='#ref{ref_map[matches[1]]}'>[{ref_map[matches[1]]}]</a>"


def insert_dates(txt):
    now = datetime.now()
    txt = txt.replace("{{date:Y}}", now.strftime("%Y"))
    txt = txt.replace("{{date:D-M-Y}}", now.strftime("%d-%B-%Y"))

    return txt


def python_highlight(txt):
    txt = txt.replace(" ", "&nbsp;")
    out = []
    for line in txt.split("\n"):
        comment = ""
        if "#" in line:
            lsp = line.split("#", 1)
            line = lsp[0]
            comment = f"<span style='color:#FF8800'>#{lsp[1]}</span>"

        lsp = line.split("\"")
        line = lsp[0]

        for i, j in enumerate(lsp[1:]):
            if i % 2 == 0:
                line += f"<span style='color:#DD2299'>\"{j}"
            else:
                line += f"\"</span>{j}"

        out.append(line + comment)
    return "<br />".join(out)


def markup_person(details):
    out = "<div class='person'>"
    info = {}
    for line in details.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()

    if "img" in info:
        out += f"<div class='imgwrap'><img src='{info['img']}'></div>\n"
    else:
        out += "<div class='imgwrap'><img src='/img/faceholder.png'></div>\n"
    out += "<div class='innertext'>\n"
    out += f"<h3>{info['name']}</h3>\n{info['about']}"
    if "rust-about" in info:
        out += f" {info['rust-about']}"
    out += "<ul class='sociallist'>"
    if "email" in info:
        out += f"<li><a href='mailto:{info['email']}'><i class='far fa-envelope'></i>&nbsp;"
        out += info["email"]
        out += "</a></li>"
    if "website" in info:
        out += f"<li><a href='{info['website']}'><i class='fab fa-internet-explorer'></i>&nbsp;"
        out += info["website"].split("://")[1]
        out += "</a></li>"
    if "github" in info:
        out += f"<li><a href='https://github.com/{info['github']}'>"
        out += "<i class='fab fa-github'></i>&nbsp;"
        out += info["github"]
        out += "</a></li>"
    if "mastodon" in info:
        username, domain = info['mastodon'].split('@')
        out += f"<li><a href='https://{domain}/@{username}'>"
        out += "<i class='fab fa-mastodon'></i>&nbsp;"
        out += "@" + info["mastodon"]
        out += "</a></li>"
    if "twitter" in info:
        out += f"<li><a href='https://twitter.com/{info['twitter']}'>"
        out += "<i class='fab fa-twitter'></i>&nbsp;"
        out += "@" + info["twitter"]
        out += "</a></li>"

    out += "</ul></div></div>"
    return out
