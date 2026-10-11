#!/usr/bin/env python3
"""Turn the approved redesign preview into the live index.html.

- adds the full document head (meta, self-hosted fonts, favicon)
- removes the preview banner
- wires the contact form to the CWS contact Google Form (same IDs as before)
"""
import re
import sys
from pathlib import Path

SRC = Path("/home/claude/cws-preview/cws-redesign-preview.html")
OUT = Path("/home/claude/cws-strategies/index.html")

src = SRC.read_text()

def swap(old, new, count=1):
    global src
    n = src.count(old)
    if n != count:
        sys.exit(f"expected {count} match(es), found {n}: {old[:70]!r}")
    src = src.replace(old, new)

# 1. Fonts: Google Fonts links -> self-hosted @font-face (files already in /fonts)
src = re.sub(r'<title>.*?</title>\s*', '', src, count=1)
src = re.sub(r'<link rel="preconnect"[^>]*>\s*<link rel="preconnect"[^>]*>\s*<link rel="stylesheet"[^>]*>\s*', '', src, count=1)
swap('<style>\n', '''<style>
@font-face{font-family:"Source Serif 4";font-weight:600;font-style:normal;font-display:swap;src:url(fonts/source-serif-4-latin-600-normal.woff2) format("woff2")}
@font-face{font-family:"Work Sans";font-weight:400;font-style:normal;font-display:swap;src:url(fonts/work-sans-latin-400-normal.woff2) format("woff2")}
@font-face{font-family:"Work Sans";font-weight:500;font-style:normal;font-display:swap;src:url(fonts/work-sans-latin-500-normal.woff2) format("woff2")}
@font-face{font-family:"Work Sans";font-weight:600;font-style:normal;font-display:swap;src:url(fonts/work-sans-latin-600-normal.woff2) format("woff2")}
''')

# 2. Remove the preview banner
swap('.preview-bar{background:#FFF6D6;color:#5A4400;font-size:14px;text-align:center;padding:8px 16px;border-bottom:1px solid #EAD9A0}\n', '')
swap('<div class="preview-bar">Preview only. Nothing here is live, and the form below doesn\'t send.</div>\n\n', '<a class="skip" href="#main">Skip to content</a>\n\n')
swap('/* header */', '.skip{position:absolute;left:-9999px;top:0;background:var(--black);color:var(--white);padding:10px 16px;z-index:60}\n.skip:focus{left:16px;top:16px}\n.hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}\n.form-status{font-size:15px;color:#FF9C94}\n\n/* header */')
swap('<main>', '<main id="main">')

# 3. Form fields: names, limits, error ids, honeypot, status line
fields = [
    ('f-name', 'name', 'maxlength="120" aria-describedby="e-name" required'),
    ('f-email', 'email', 'inputmode="email" maxlength="200" aria-describedby="e-email" required'),
    ('f-org', 'org', 'maxlength="160" aria-describedby="e-org" required'),
    ('f-site', 'website', 'maxlength="300" aria-describedby="e-site"'),
]
for fid, name, extra in fields:
    src, n = re.subn(rf'<input id="{fid}" ([^>]*)>(<p class="err")>', rf'<input id="{fid}" name="{name}" \1 {extra}>\2 id="e-{fid[2:]}">', src)
    if n != 1:
        sys.exit(f"field {fid} not found")
swap('<textarea id="f-msg"></textarea><p class="err">', '<textarea id="f-msg" name="message" maxlength="4000" aria-describedby="e-msg" required></textarea><p class="err" id="e-msg">')
swap('<div class="actions"><button class="btn send" type="submit" id="f-submit" aria-disabled="true">Send message</button><p class="hint" id="f-hint">Fill in the required fields to send.</p></div>',
     '<div class="hp" aria-hidden="true"><label for="f-hp">Leave this field empty</label><input id="f-hp" name="fax" type="text" tabindex="-1" autocomplete="off"></div>\n'
     '          <div class="actions"><button class="btn send" type="submit" id="f-submit" aria-disabled="true" aria-describedby="f-hint">Send message</button><p class="hint" id="f-hint">Fill in the required fields to send.</p></div>\n'
     '          <p class="form-status" id="f-status" role="alert"></p>')

# 4. Real submission instead of the preview's mock
start = src.index('  form.addEventListener("submit"')
end = src.index('})();\n</script>')
src = src[:start] + r'''  var FORM_URL="https://docs.google.com/forms/d/e/1FAIpQLScYDmCF14dDMJJ2Nt8sbKEqnm21TGS7uRCq6vpMyEAAnKSSEw/formResponse";
  var ENTRY={name:"entry.1776780043",email:"entry.1060079209",org:"entry.596398298",website:"entry.1288896526",message:"entry.1720886323"};
  var status=document.getElementById("f-status"), loadedAt=Date.now();
  form.addEventListener("submit",function(e){
    e.preventDefault(); status.textContent="";
    if(btn.dataset.busy)return;
    if(!fields.every(ok)){var first=null;fields.forEach(function(f){f.dataset.touched="1";if(!show(f,true)&&!first)first=f;});if(first)ctl(first).focus();return;}
    var v=function(id){return document.getElementById(id).value.trim();};
    var data={name:v("f-name"),email:v("f-email"),org:v("f-org"),website:v("f-site"),message:v("f-msg")};
    var isBot=v("f-hp")!==""||Date.now()-loadedAt<3000;
    var body=new URLSearchParams(); Object.keys(ENTRY).forEach(function(k){body.append(ENTRY[k],data[k]);});
    btn.dataset.busy="1"; btn.textContent="Sending…";
    (isBot?Promise.resolve():fetch(FORM_URL,{method:"POST",mode:"no-cors",body:body})).then(function(){
      var area=document.getElementById("form-area");
      area.innerHTML='<div class="thanks" tabindex="-1" id="thanks"><h3>Thanks, <span></span>. Message received.</h3><p>We’ll reply to <strong></strong> soon. In the meantime, nothing else is needed from you.</p></div>';
      var t=document.getElementById("thanks");t.querySelector("span").textContent=data.name.split(/\s+/)[0];t.querySelector("strong").textContent=data.email;t.focus();
    }).catch(function(){delete btn.dataset.busy;btn.textContent="Send message";status.textContent="Something went wrong sending your message. Please check your connection and try again.";});
  });
''' + src[end:]
swap('<div class="legal"><span>© 2026 CWS, LLC.', '<div class="legal"><span>© <span id="yr">2026</span> CWS, LLC.')
swap('document.documentElement.classList.add("js");', 'document.documentElement.classList.add("js");\ndocument.getElementById("yr").textContent=new Date().getFullYear();')

head = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>CWS Strategies | Web Design, Apple Apps &amp; Salesforce Administrator</title>
<meta name="description" content="CWS Strategies is a woman-owned Kentucky firm building websites, iPhone, iPad and Mac apps, and Salesforce Administrator support for small businesses and nonprofits.">
<meta property="og:title" content="CWS Strategies">
<meta property="og:description" content="Websites, Apple apps, and Salesforce Administrator support, built for small teams.">
<meta property="og:type" content="website">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preload" href="fonts/source-serif-4-latin-600-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/work-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
'''
# split style block into head, the rest into body
style_end = src.index('</style>') + len('</style>')
OUT.write_text(head + src[:style_end].lstrip() + '\n</head>\n<body>\n' + src[style_end:].lstrip() + '\n</body>\n</html>\n')
print("wrote", OUT, len(OUT.read_text()), "bytes")
