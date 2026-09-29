import urllib.request
from bs4 import BeautifulSoup
import re

headers = {'User-Agent': 'Mozilla/5.0'}

def probe_district(district_name, base_url_pattern, max_pages=15):
    print(f"\n================ probing {district_name} ================")
    la_docs = []
    for p in range(1, max_pages + 1):
        url = base_url_pattern.format(p)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                soup = BeautifulSoup(resp.read(), 'html.parser')
                tables = soup.find_all('table')
                if not tables:
                    break
                rows = tables[0].find_all('tr')[1:]
                if not rows:
                    break
                for r in rows:
                    tds = r.find_all('td')
                    if len(tds) >= 3:
                        title = tds[0].get_text(strip=True)
                        date = tds[1].get_text(strip=True) if len(tds) > 1 else ''
                        a = tds[-1].find('a') or tds[0].find('a')
                        href = a['href'] if a and a.has_attr('href') else ''
                        if any(k in title.lower() for k in ['acquisition', 'award', '11(1)', '19(1)', '21', 'भूसंपादन', 'निवाडा', 'section']):
                            print(f"[{district_name}] P{p} | {date} | {title} | {href}")
                            la_docs.append({'title': title, 'date': date, 'url': href, 'page': p})
        except Exception as e:
            # print(f"Page {p} err: {e}")
            break
    print(f"Total LA docs in {district_name}: {len(la_docs)}")
    return la_docs

if __name__ == '__main__':
    probe_district('Pune Docs', 'https://pune.gov.in/en/documents/page/{}/')
    probe_district('Nashik Docs', 'https://nashik.gov.in/en/documents/page/{}/')
    probe_district('Yavatmal Docs', 'https://yavatmal.gov.in/en/documents/page/{}/')
    probe_district('Solapur Docs', 'https://solapur.gov.in/en/documents/page/{}/')
