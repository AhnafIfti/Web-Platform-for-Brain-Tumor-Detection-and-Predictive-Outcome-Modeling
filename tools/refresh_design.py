"""Apply the requested visible vocabulary and glass-panel design classes."""
import re
from pathlib import Path

for path in Path('templates').rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    # Preserve Django routes, field names, CSS selectors, and internal identifiers.
    chunks = re.split(r'({%.*?%}|{{.*?}}|<[^>]*>)', text, flags=re.S)
    for i, chunk in enumerate(chunks):
        if not chunk.startswith(('<', '{%','{{')):
            chunk = chunk.replace('RESEARCH BETA', 'AI WORKSPACE')
            chunk = chunk.replace('RESEARCH USE ONLY', 'EXPERIMENTAL AI')
            chunk = chunk.replace('Research use only', 'Experimental AI')
            chunk = chunk.replace('Research & educational use only', 'Educational use · Not a diagnosis')
            chunk = chunk.replace('Research decision-support prototype', 'AI-assisted analysis')
            chunk = chunk.replace('PRECISION THROUGH RESEARCH', 'INTELLIGENCE IN EVERY LAYER')
            chunk = chunk.replace('research and educational use only', 'educational use only')
            chunk = chunk.replace('research and education', 'education and exploration')
            chunk = re.sub(r'\bRESEARCH\b', 'INSIGHTS', chunk)
            chunk = re.sub(r'\bResearch\b', 'Model insights', chunk)
            chunk = re.sub(r'\bresearch\b', 'analysis', chunk)
            chunks[i] = chunk
    text = ''.join(chunks)
    text = re.sub(r'class="panel(?=[ "])', 'class="panel backdrop-blur-xl shadow-2xl shadow-black/20 border-white/10', text)
    text = re.sub(r'class="metric-card(?=[ "])', 'class="metric-card backdrop-blur-xl shadow-xl shadow-cyan-950/20 transition duration-300 hover:-translate-y-1', text)
    text = text.replace('class="button primary', 'class="button primary transition duration-300 hover:shadow-lg hover:shadow-cyan-400/20')
    text = text.replace("<link rel=\"stylesheet\" href=\"{% static 'css/app.css' %}\">", "<link rel=\"stylesheet\" href=\"{% static 'css/tailwind.css' %}\"><link rel=\"stylesheet\" href=\"{% static 'css/app.css' %}\"><link rel=\"stylesheet\" href=\"{% static 'css/glass.css' %}\">")
    path.write_text(text, encoding='utf-8')
