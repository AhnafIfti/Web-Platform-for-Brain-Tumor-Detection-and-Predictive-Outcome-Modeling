"""Extract stored HTML table ONLY; never execute notebook code or invent metrics."""
import argparse
import csv
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        if tag in ('td', 'th'):
            self.cell = ''

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(self.cell.strip())
            self.cell = None
        if tag == 'tr':
            self.rows.append(self.row)


def extract(source, destination):
    data = source.read_bytes()
    notebook = json.loads(data)
    for index, cell in enumerate(notebook['cells']):
        if 'model_comparison_full.csv' not in ''.join(cell.get('source', [])):
            continue
        for output in cell.get('outputs', []):
            html = ''.join(output.get('data', {}).get('text/html', []))
            if not html:
                continue
            parser = TableParser()
            parser.feed(html)
            rows = [row[1:] for row in parser.rows if len(row) == 7]
            if not rows or rows[0][0] != 'Model':
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('w', newline='', encoding='utf-8') as stream:
                csv.writer(stream).writerows(rows)
            provenance = {'source': source.name, 'sha256': hashlib.sha256(data).hexdigest(),
                          'cell_index': index, 'output': 'stored text/html', 'rows': len(rows) - 1,
                          'limitations': 'Historical saved outputs, rounded to four decimals. No upgraded v2 results. Notebook source was edited after some executions; run configuration cannot be certified.'}
            destination.with_suffix('.provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
            print(json.dumps(provenance, indent=2))
            return
    raise RuntimeError('No stored full benchmark table found.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('notebook', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    extract(args.notebook, args.destination)
