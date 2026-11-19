#!/usr/bin/env python3
"""Собирает свой маленький файл телепрограммы epg.xml.gz только для каналов из all.m3u.
Израиль берётся из open-epg, остальные каналы из iptvx.one, каналы 10 и 16 из epg.team. Только вперёд: сейчас идущая передача и ближайшие 3 дня."""
import gzip, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

SOURCES = ['https://www.open-epg.com/files/israel.xml.gz', 'https://iptvx.one/EPG', 'https://epg.team/1.1.xml.gz']  # epg.team: только ערוץ 10 и ערוץ 16
DAYS = 3

def parse_time(s):
    return datetime.strptime(s.strip()[:20], '%Y%m%d%H%M%S %z') if ' ' in s.strip() else \
        datetime.strptime(s.strip()[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)

def main(m3u, out):
    wanted = set(re.findall(r'tvg-id="([^"]+)"', open(m3u, encoding='utf-8').read()))
    now = datetime.now(timezone.utc); end = now + timedelta(days=DAYS)
    chans, progs, have = [], [], set()
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            raw = urllib.request.urlopen(req, timeout=300)
            f = gzip.GzipFile(fileobj=raw)
            got = set()
            for ev, el in ET.iterparse(f, events=('end',)):
                if el.tag == 'channel':
                    cid = el.get('id')
                    if cid in wanted and cid not in have:
                        chans.append(ET.tostring(el, encoding='unicode')); got.add(cid)
                    el.clear()
                elif el.tag == 'programme':
                    cid = el.get('channel')
                    if cid in got:
                        try:
                            if parse_time(el.get('stop')) > now and parse_time(el.get('start')) < end:
                                progs.append(ET.tostring(el, encoding='unicode'))
                        except Exception:
                            pass
                    el.clear()
            have |= got
            print(url, 'каналов', len(got))
        except Exception as e:
            print('ОШИБКА', url, e, file=sys.stderr)
    if not progs:
        print('пусто, старый файл остаётся', file=sys.stderr); return
    with gzip.open(out, 'wt', encoding='utf-8') as g:
        g.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n' + '\n'.join(chans) + '\n' + '\n'.join(progs) + '\n</tv>\n')
    print('готово: каналов', len(have), 'передач', len(progs))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
