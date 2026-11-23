#!/usr/bin/env python3
"""Usage: publish.py item.md

Adds (or replaces same-day) the item in items.json, keeps the latest 14 items,
rebuilds feed.xml, commits and pushes.

At publish time, emoji and other pictographic symbols are replaced with small
embedded <img> tags (Twemoji PNGs as data:image URIs) so e-readers such as
PocketBook that cannot fetch remote images may still show the icons.
"""
import sys,re,html,email.utils,datetime,subprocess,zoneinfo,os,json
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emojiimg
emojiimg.setup('icons', 'https://icemonk79.github.io/citaonica-rss/icons')
if len(sys.argv)<2:
    sys.exit('Usage: publish.py <item.md>')
md=open(sys.argv[1],encoding='utf-8').read()

def inline(s):
    s=html.escape(s,quote=False)
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'\*(.+?)\*',r'<i>\1</i>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    return s

out=[];inl=None  # None | 'ul' | 'ol'
def close_list():
    global inl
    if inl:
        out.append('</'+inl+'>')
        inl=None

# first markdown H1 becomes the item title; remaining headings stay in the body
item_title=None
for l in md.split('\n'):
    l=l.rstrip()
    m=re.match(r'^(#{1,6}) (.+)$',l)
    if m:
        close_list()
        level=len(m.group(1)); text=m.group(2).strip()
        if item_title is None and level==1:
            item_title=emojiimg.replace_plain(text)
            continue
        tag='h2' if level<=2 else 'h3'
        out.append('<'+tag+'>'+inline(text)+'</'+tag+'>')
    elif re.match(r'[-*] ',l):
        if inl!='ul':
            close_list(); out.append('<ul>'); inl='ul'
        out.append('<li>'+inline(l[2:])+'</li>')
    elif re.match(r'\d+\. ',l):
        if inl!='ol':
            close_list(); out.append('<ol>'); inl='ol'
        out.append('<li>'+inline(re.sub(r'^\d+\. ','',l))+'</li>')
    elif l.startswith('> '):
        close_list()
        out.append('<blockquote><p>'+inline(l[2:])+'</p></blockquote>')
    elif l.strip():
        close_list()
        out.append('<p>'+inline(l)+'</p>')
close_list()
body=emojiimg.replace_html('\n'.join(out).replace(']]>',']]&gt;'))
if not item_title:
    sys.exit('Nedostaje naslov: markdown mora da počinje sa "# naslov"')

now=datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Belgrade'))
pub=email.utils.format_datetime(now)
guid=f"citaonica-{now:%Y-%m-%d}"
link='https://icemonk79.github.io/citaonica-rss/'
entry=dict(title=item_title,guid=guid,pubDate=pub,html=body,ts=now.timestamp(),
           link=link+'#'+guid)
items=json.load(open('items.json',encoding='utf-8')) if os.path.exists('items.json') else []
# replace same calendar day if we re-publish
items=[e for e in items if e.get('guid')!=guid]
items.append(entry)
items=sorted(items,key=lambda e:e.get('ts',0),reverse=True)[:14]

def item(e):
    html_body=emojiimg.replace_html(e['html'])
    return '''<item>
<title>'''+html.escape(emojiimg.replace_plain(e['title']))+'''</title>
<link>'''+e.get('link',link)+'''</link>
<guid isPermaLink="false">'''+e['guid']+'''</guid>
<pubDate>'''+e['pubDate']+'''</pubDate>
<description><![CDATA['''+html_body+''']]></description>
<content:encoded><![CDATA['''+html_body+''']]></content:encoded>
</item>'''

xml='''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>Čitaonica</title>
<link>'''+link+'''</link>
<description>Dnevni sažeci knjiga i kratka objašnjenja tema, pisani da se lakše čitaju</description>
<language>sr</language>
<lastBuildDate>'''+items[0]['pubDate']+'''</lastBuildDate>
'''+chr(10).join(item(e) for e in items)+'''
</channel>
</rss>
'''
from xml.dom import minidom as _minidom; _minidom.parseString(xml.encode())
json.dump(items,open('items.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
open('feed.xml','w',encoding='utf-8').write(xml)
g=['git','-c','user.name=icemonk79','-c','user.email=icemonk79@users.noreply.github.com']
if os.path.isdir('.git'):
    subprocess.run(['git','pull','-q','--rebase'],check=False)
    subprocess.run(['git','add','feed.xml','items.json','icons','emojiimg.py','publish.py',
                    'index.html','.nojekyll','history.txt','README.md','.gitignore','items'],check=True)
    subprocess.run(g+['commit','-qm',item_title],check=False)
    if os.environ.get('SKIP_PUSH')!='1':
        subprocess.run(['git','push','-q'],check=True)
print('published',item_title)
