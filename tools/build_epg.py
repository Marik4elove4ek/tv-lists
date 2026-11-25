#!/usr/bin/env python3
"""Собирает свой маленький файл телепрограммы epg.xml.gz только для каналов из all.m3u.
Израиль берётся из open-epg, остальные каналы из iptvx.one, каналы 10 и 16 из epg.team. Только вперёд: сейчас идущая передача и ближайшие 3 дня."""
import gzip, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

SOURCES = ['https://www.open-epg.com/files/israel.xml.gz', 'https://www.open-epg.com/files/georgia1.xml.gz', 'https://iptvx.one/EPG', 'https://epg.team/1.1.xml.gz', 'https://epgshare01.online/epgshare01/epg_ripper_NL1.xml.gz', 'https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz', 'https://epgshare01.online/epgshare01/epg_ripper_US1.xml.gz']  # epgshare01: только каналы 18+ по названию  # epg.team: только ערוץ 10 и ערוץ 16
DAYS = 3

# Каналы 18+ в источниках называются по-разному и без общего кода — находим их по названию
# и записываем под своим кодом (такой же tvg-id стоит у канала в плейлисте)
ADULT = {
    'adult-playboy': r'^playboy( tv)?( hd)?$', 'adult-russkaya-noch': r'^(русская ночь|russkaya noch|russian night)',
    'adult-babes': r'^babes( tv)?( hd)?$', 'adult-barely-legal': r'^barely legal', 'adult-blue-hustler': r'^blue hustler',
    'adult-brazzers': r'^brazzers( tv)?( europe| europa)?( hd)?$', 'adult-desire': r'^desire( tv)?( hd)?$',
    'adult-dorcel': r'^dorcel( tv)?( hd)?$', 'adult-erox': r'^erox( hd)?$', 'adult-eroxxx': r'^eroxxx( hd)?$',
    'adult-extasy': r'^extasy( 4k| hd| platinum)?', 'adult-exxxotika': r'^exxxoti[ck]a', 'adult-hustler': r'^hustler( tv)?( hd| europe)?$',
    'adult-passionxxx': r'^passion ?xxx', 'adult-porn-classic': r'^porn classic', 'adult-private': r'^private( tv)?( hd)?$',
    'adult-redlight': r'^red ?light( hd)?', 'adult-rktv': r'^rk ?tv',
}
def norm(n): return re.sub(r'[\s_]+', ' ', (n or '').strip().lower())

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
            got = set(); alias = {}
            for ev, el in ET.iterparse(f, events=('end',)):
                if el.tag == 'channel':
                    cid = el.get('id')
                    if cid in wanted and cid not in have:
                        chans.append(ET.tostring(el, encoding='unicode')); got.add(cid)
                    else:
                        names = [norm(d.text) for d in el.findall('display-name')]
                        for a, pat in ADULT.items():
                            if a in wanted and a not in have and a not in alias.values() and any(re.search(pat, n) for n in names):
                                alias[cid] = a; el.set('id', a)
                                chans.append(ET.tostring(el, encoding='unicode')); got.add(a)
                                break
                    el.clear()
                elif el.tag == 'programme':
                    cid = el.get('channel')
                    if cid in alias: el.set('channel', alias[cid]); cid = alias[cid]
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
