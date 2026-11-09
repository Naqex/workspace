"""Extract official archive release dates, never infer actual publication times."""
from collections import Counter
from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse

ARCHIVE = 'https://www.eia.gov/petroleum/supply/weekly/archive/'
PATH = re.compile(r'/petroleum/supply/weekly/archive/(?P<year>\d{4})/(?P<day>\d{4}_\d{2}_\d{2})/wpsr_(?P=day)\.php')
# EIA press507 confirms these delayed data were released with June24 on June29.
DELAYED_DATA = '/petroleum/supply/weekly/archive/2022/2022_06_17_data/wpsr_2022_06_17_data.php'


class ArchiveLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.records = []; self.active = None; self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.active = next((v for k,v in attrs if k=='href'),None); self.text = []

    def handle_data(self, data):
        if self.active is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.active is not None:
            self.records.append((self.active,''.join(self.text).strip()))
            self.active = None; self.text = []


def release_dates(html, *, years=(2019, 2022)):
    if tuple(years) != (2019, 2022):
        raise ValueError('registered_calendar_years_only')
    parser = ArchiveLinks(); parser.feed(html); links = Counter(); sources = {}
    for href, label in parser.records:
        url = urlparse(urljoin(ARCHIVE, href))
        prefix = re.match(r'/petroleum/supply/weekly/archive/(\d{4})/', url.path)
        if not prefix or int(prefix[1]) not in years:
            continue
        if url.scheme != 'https' or url.netloc != 'www.eia.gov' or url.query or url.fragment:
            raise ValueError('official_archive_origin_required')
        if url.path == DELAYED_DATA:
            if label != '29':
                raise ValueError('delayed_data_release_label_mismatch')
            day = date(2022,6,29)
        else:
            match = PATH.fullmatch(url.path)
            if not match:
                raise ValueError('archive_date_path_mismatch')
            day = date.fromisoformat(match['day'].replace('_', '-'))
            if day.year != int(match['year']) or label != str(day.day):
                raise ValueError('archive_year_or_visible_release_label_mismatch')
        links[day.isoformat()] += 1
        sources.setdefault(day.isoformat(),[]).append(url.geturl())
    if {int(d[:4]) for d in links} != set(years):
        raise ValueError('both_registered_years_required')
    events = [dict(release_date=d, archive_link_occurrences=count,
                   source_urls=sources[d],
                   weekday=date.fromisoformat(d).strftime('%A'),
                   actual_release_time_et=None, publication_time_verified=False,
                   preannouncement_schedule_verified=False, trading_eligibility_verified=False)
              for d, count in sorted(links.items())]
    return dict(schema='eia-official-archive-release-dates-v1', years=list(years),
                events=events, source_link_occurrences=sum(links.values()),
                unique_release_dates=len(events), duplicate_date_occurrences=sum(c-1 for c in links.values()),
                event_times_inferred=False, market_prices_read=False,
                execution_authorized=False, holdout_prices_read=False)
